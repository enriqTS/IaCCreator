"""Dynamic ECS fault targets retain native ownership and bounded IAM scope."""

import json
import re
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.fis_ecs import ecs_fault_preconditions
from app.models.connection_configs.fis import SELECTION_MODES
from app.models.connection_configs.fis_ecs import FisEcsConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_ecs_logs_connections import mixed_architecture as logs_architecture
from tests.test_eks_prometheus_connections import evaluate
from tests.test_fis_ec2_connections import architecture as ec2_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate, project
from tests.test_secret_connections import architecture as secret_architecture


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.FAULT_INJECTION_SIMULATOR, ServiceType.ECS, None, {})
    )


def native_values():
    return {
        "var.role_arn": "arn:aws:iam::123456789012:role/fis/experiment",
        "var.action_name": "fault_action",
        "var.fis_ecs_service": {
            "cluster_arn": "arn:aws:ecs:us-east-1:123456789012:cluster/application",
            "cluster_name": "application",
            "service_arn": "arn:aws:ecs:us-east-1:123456789012:service/application/web",
            "service_name": "web",
        },
        "var.fis_ecs_selection": "COUNT(1)",
        "data.aws_partition.experiment.partition": "aws",
        "data.aws_region.experiment.region": "us-east-1",
        "data.aws_caller_identity.experiment.account_id": "123456789012",
        "local.fis_ecs_task_arn": "arn:aws:ecs:us-east-1:123456789012:task/application/*",
    }


def policy_expression(tree):
    return re.search(
        r"  policy = (.*?)\n  lifecycle \{", file_with(tree, "/ecs_targets.tf"), re.S
    )[1]


def fault_policies(tree):
    return [
        item
        for item in resources(tree, "aws_iam_role_policy")
        if item.get("name_prefix") == "fis-ecs-"
    ]


def test_template_uses_service_parameters_and_running_task_filter():
    tree = generate(architecture())
    template = resources(tree, "aws_fis_experiment_template")[0]
    action = template["action"][0]
    assert action["action_id"] == "aws:ecs:stop-task"
    assert action["name"] == "${var.action_name}"
    assert action["target"][0]["key"] == "Tasks"
    assert action["target"][0]["value"] == "managed_ecs"
    assert "parameter" not in action
    target = template["target"][0]
    assert target["name"] == "managed_ecs"
    assert target["resource_type"] == "aws:ecs:task"
    assert target["parameters"] == {
        "cluster": "${var.fis_ecs_service.cluster_name}",
        "service": "${var.fis_ecs_service.service_name}",
    }
    assert target["filter"][0]["path"] == "LastStatus"
    assert target["filter"][0]["values"] == ["RUNNING"]
    assert target["selection_mode"] == "${var.fis_ecs_selection}"
    assert "resource_tag" not in target and "resource_arns" not in target
    assert template["depends_on"] == ["${aws_iam_role_policy.fis_ecs}"]
    assert len(template["lifecycle"][0]["precondition"]) == 6
    assert template["stop_condition"][0]["source"] == "none"
    policy = fault_policies(tree)[0]
    assert policy["name_prefix"] == "fis-ecs-"
    assert policy["role"] == "${data.aws_iam_role.fis_ecs.name}"
    assert len(policy["lifecycle"][0]["precondition"]) == 7
    assert all(
        item["name"] == "target-resource-role"
        for item in resources(tree, "aws_iam_role")
    )
    assert not resources(tree, "aws_fis_experiment")
    assert not resources(tree, "aws_ssm_association")
    assert "fis_ecs_service = module.target-resource.fis_service" in file_with(
        tree, "/environments/dev/main.tf"
    )
    outputs = file_with(tree, "/target-resource/outputs.tf")
    for field in (
        "aws_ecs_cluster.target-resource.arn",
        "aws_ecs_cluster.target-resource.name",
        "aws_ecs_service.target-resource_service.id",
        "aws_ecs_service.target-resource_service.name",
    ):
        assert field in outputs
    assert "module.source-resource" not in outputs
    result = ConnectionProcessor().process_all(project(architecture()))
    assert {(item.module, item.filename) for item in result.resources} == {
        ("source-resource", "ecs_targets.tf")
    }
    assert not result.iam


@given(
    name=resource_name_st,
    selection=st.sampled_from(SELECTION_MODES),
    duplicates=st.integers(1, 4),
)
@settings(max_examples=20, deadline=None)
def test_selection_names_and_duplicates_are_order_independent(
    name, selection, duplicates
):
    payload = architecture()
    name = f"target-{name}"
    payload["resources"][1]["name"] = name
    payload["connections"][0].update(
        target=name, connection_config={"selection_mode": selection}
    )
    tree = generate(payload)
    assert len(fault_policies(tree)) == 1
    assert len(resources(tree, "aws_fis_experiment_template")[0]["target"]) == 1
    payload["connections"] = list(reversed(payload["connections"] * duplicates))
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "config",
    [
        {"selection_mode": "COUNT(0)"},
        {"selection_mode": "COUNT(6)"},
        {"selection_mode": "PERCENT(50)"},
        {"selection_mode": "ALL "},
        {"selection_mode": True},
        {"selection_mode": None},
        {"operation": "stop"},
        {"cluster": "other"},
        {"service": "other"},
        {"unknown": True},
    ],
)
def test_invalid_selection_and_external_target_overrides_are_rejected(config):
    with pytest.raises(ValidationError):
        FisEcsConfig.model_validate(config)
    payload = architecture()
    payload["connections"][0]["connection_config"] = config
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize(
    "field, value",
    [
        ("role_arn", ""),
        ("role_arn", "experiment"),
        ("role_arn", "arn:aws:iam::123456789012:user/fis"),
        ("role_arn", "arn:aws:iam::123456789012:role/*"),
        ("action_name", ""),
        ("action_name", "bad/name"),
        ("action_name", "x" * 65),
    ],
)
def test_invalid_source_settings_fail_generation_and_preview(field, value):
    payload = architecture()
    payload["resources"][0]["config"][field] = value
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)
    with pytest.raises(InvalidConnectionConfigError):
        ConnectionPreviewer().preview_all(project(payload))


@pytest.mark.parametrize("mode", ["selection", "service"])
def test_conflicting_target_bindings_are_rejected(mode):
    payload = architecture()
    edge = deepcopy(payload["connections"][0])
    if mode == "selection":
        edge["connection_config"] = {"selection_mode": "ALL"}
    else:
        payload["resources"].append(
            dict(
                deepcopy(payload["resources"][1]),
                name="other-service",
                id="other-service",
            )
        )
        edge.update(target="other-service", target_id="other-service")
    payload["connections"].append(edge)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize("reverse", [True, False])
def test_mixed_ec2_and_ecs_templates_are_rejected_before_contribution(reverse):
    payload = architecture()
    instance = ec2_architecture()
    payload["resources"].append(
        dict(instance["resources"][1], name="instance", id="instance")
    )
    payload["connections"].append(
        dict(instance["connections"][0], target="instance", target_id="instance")
    )
    if reverse:
        payload["connections"].reverse()
    with pytest.raises(InvalidConnectionConfigError, match="one target service type"):
        generate(payload)
    with pytest.raises(InvalidConnectionConfigError, match="one target service type"):
        ConnectionPreviewer().preview_all(project(payload))


def test_effective_regions_include_environment_overrides():
    payload = architecture()
    payload["resources"][1]["provider_region"] = "eu-west-1"
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)
    payload["environments"][0]["variables"]["region"] = "eu-central-1"
    assert generate(payload)


def test_connection_overrides_action_without_changing_ecs_resources():
    payload = architecture()
    payload["resources"][0]["config"]["action_id"] = "aws:fis:wait"
    connected = generate(payload)
    payload["connections"] = []
    standalone = generate(payload)
    for resource_type in (
        "aws_ecs_cluster",
        "aws_ecs_task_definition",
        "aws_ecs_service",
    ):
        assert resources(connected, resource_type) == resources(
            standalone, resource_type
        )
    assert (
        resources(standalone, "aws_fis_experiment_template")[0]["action"][0][
            "action_id"
        ]
        == "${var.action_id}"
    )
    assert not fault_policies(standalone)
    assert resources(connected, "aws_iam_role") == resources(standalone, "aws_iam_role")
    assert 'output "fis_service"' not in file_with(
        standalone, "/target-resource/outputs.tf"
    )


def test_preview_explains_dynamic_selection_cluster_permissions_and_replacement():
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    assert {item.resource_type for item in preview.resources} == {"aws_iam_role_policy"}
    message = " ".join(issue.message for issue in preview.issues)
    for text in (
        "does not start",
        "running tasks",
        "one ECS service",
        "fis.amazonaws.com",
        "iam:GetRole",
        "throughout the connected cluster",
        "not an IAM boundary",
        "unavailable selection count",
        "stops all its containers",
        "scheduler may replace",
        "source=none",
        "SSM sidecars",
    ):
        assert text in message


@needs_terraform
@pytest.mark.parametrize(
    "partition, region, cluster",
    [("aws", "us-east-1", "application"), ("aws-cn", "cn-north-1", "Application_2")],
)
def test_actual_policy_scopes_task_operations_and_cluster_discovery(
    tmp_path, partition, region, cluster
):
    values = native_values()
    cluster_arn = f"arn:{partition}:ecs:{region}:123456789012:cluster/{cluster}"
    task_arn = f"arn:{partition}:ecs:{region}:123456789012:task/{cluster}/*"
    values["var.fis_ecs_service"]["cluster_arn"] = cluster_arn
    values["data.aws_region.experiment.region"] = region
    values["local.fis_ecs_task_arn"] = task_arn
    policy = json.loads(
        evaluate(tmp_path, policy_expression(generate(architecture())), values)
    )
    tasks, discovery, tags = policy["Statement"]
    cluster_condition = {
        "ArnEquals": {"ecs:cluster": cluster_arn},
        "StringEquals": {"aws:RequestedRegion": region},
    }
    assert tasks == {
        "Effect": "Allow",
        "Action": ["ecs:DescribeTasks", "ecs:StopTask"],
        "Resource": task_arn,
        "Condition": cluster_condition,
    }
    assert discovery == {
        "Effect": "Allow",
        "Action": ["ecs:ListTasks"],
        "Resource": "*",
        "Condition": cluster_condition,
    }
    assert tags == {
        "Effect": "Allow",
        "Action": ["tag:GetResources"],
        "Resource": "*",
        "Condition": {"StringEquals": {"aws:RequestedRegion": region}},
    }
    assert "ssm:" not in json.dumps(policy) and "ecs:RunTask" not in json.dumps(policy)
    locals_expression = re.search(
        r"  fis_ecs_task_arn = (.*)\n",
        file_with(generate(architecture()), "/ecs_targets.tf"),
    )[1]
    assert evaluate(tmp_path, locals_expression, values) == task_arn


@needs_terraform
@pytest.mark.parametrize(
    "index, mutation",
    [
        (0, {"role_arn": "arn:aws:iam::999999999999:role/fis"}),
        (0, {"role_arn": "arn:aws-cn:iam::123456789012:role/fis"}),
        (0, {"role_arn": "arn:aws:iam::123456789012:role/*"}),
        (1, {"cluster_arn": "arn:aws:ecs:us-east-1:123456789012:cluster/*"}),
        (1, {"cluster_arn": "arn:aws:ecs:eu-west-1:123456789012:cluster/application"}),
        (1, {"cluster_arn": "arn:aws:ecs:us-east-1:999999999999:cluster/application"}),
        (
            1,
            {
                "cluster_arn": "arn:aws-cn:ecs:us-east-1:123456789012:cluster/application"
            },
        ),
        (
            1,
            {
                "cluster_arn": "arn:aws:ecs:us-east-1:123456789012:service/application/web"
            },
        ),
        (2, {"cluster_name": "other"}),
        (2, {"cluster_name": "*"}),
        (2, {"cluster_name": ""}),
        (3, {"service_name": "*"}),
        (3, {"service_name": ""}),
        (3, {"service_name": "other"}),
        (3, {"service_arn": "arn:aws:ecs:us-east-1:123456789012:service/other/web"}),
        (3, {"service_arn": "arn:aws:ecs:us-east-1:123456789012:service/web"}),
        (4, {"selection": "COUNT(0)"}),
        (4, {"selection": "COUNT(6)"}),
        (4, {"selection": "PERCENT(50)"}),
        (5, {"action_name": "bad/name"}),
        (5, {"action_name": "x" * 65}),
    ],
)
def test_native_guards_reject_unsafe_module_overrides(tmp_path, index, mutation):
    values = native_values()
    for key, value in mutation.items():
        if key in {"role_arn", "action_name"}:
            values[f"var.{key}"] = value
        elif key == "selection":
            values["var.fis_ecs_selection"] = value
        else:
            values["var.fis_ecs_service"][key] = value
    assert (
        evaluate(tmp_path, str(ecs_fault_preconditions()[index]["condition"]), values)
        is False
    )


@needs_terraform
@pytest.mark.parametrize("selection", SELECTION_MODES)
def test_native_guards_accept_dynamic_counts_and_all(tmp_path, selection):
    values = native_values()
    values["var.fis_ecs_selection"] = selection
    assert (
        evaluate(
            tmp_path,
            " && ".join(f"({item['condition']})" for item in ecs_fault_preconditions()),
            values,
        )
        is True
    )


@needs_terraform
@pytest.mark.parametrize("path", ["fis/", "other/", ""])
def test_policy_guard_requires_exact_role_path(tmp_path, path):
    tree = generate(architecture())
    condition = fault_policies(tree)[0]["lifecycle"][0]["precondition"][-1][
        "condition"
    ][2:-1]
    values = native_values()
    values["data.aws_iam_role.fis_ecs.arn"] = (
        f"arn:aws:iam::123456789012:role/{path}experiment"
    )
    assert evaluate(tmp_path, condition, values) is (path == "fis/")


@pytest.mark.terraform
@needs_terraform
@pytest.mark.parametrize(
    "mode",
    [
        "plain",
        "duplicate",
        "all",
        "count",
        "shared_service",
        "separate_ec2",
        "mixed",
        "observability",
        "regional",
    ],
)
def test_generated_templates_validate_and_have_acyclic_graphs(tmp_path, mode):
    payload = architecture()
    if mode == "duplicate":
        payload["connections"].append(deepcopy(payload["connections"][0]))
    elif mode in {"all", "count"}:
        payload["connections"][0]["connection_config"] = {
            "selection_mode": "ALL" if mode == "all" else "COUNT(5)"
        }
    elif mode == "shared_service":
        payload["resources"].append(
            dict(
                deepcopy(payload["resources"][0]),
                name="other-experiment",
                id="other-experiment",
            )
        )
        payload["connections"].append(
            dict(
                payload["connections"][0],
                source="other-experiment",
                source_id="other-experiment",
            )
        )
    elif mode == "separate_ec2":
        other = ec2_architecture()
        payload["resources"].extend(
            [
                dict(
                    other["resources"][0],
                    name="instance-experiment",
                    id="instance-experiment",
                ),
                dict(other["resources"][1], name="instance", id="instance"),
            ]
        )
        payload["connections"].append(
            dict(
                other["connections"][0],
                source="instance-experiment",
                source_id="instance-experiment",
                target="instance",
                target_id="instance",
            )
        )
    elif mode in {"mixed", "observability"}:
        payload = (
            logs_architecture(encrypted=True)
            if mode == "observability"
            else secret_architecture(ServiceType.ECS)
        )
        before = {
            kind: resources(generate(payload), kind)
            for kind in (
                "aws_ecs_cluster",
                "aws_ecs_task_definition",
                "aws_ecs_service",
            )
        }
        experiment = architecture()
        payload["resources"].append(
            dict(experiment["resources"][0], name="experiment", id="experiment")
        )
        payload["connections"].append(
            dict(
                experiment["connections"][0],
                source="experiment",
                source_id="experiment",
                target="source-resource",
                target_id="src",
            )
        )
        assert before == {kind: resources(generate(payload), kind) for kind in before}
    elif mode == "regional":
        for instance in payload["resources"]:
            instance["provider_region"] = "eu-west-1"
    tree = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    _write_tree(tmp_path, tree)
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
