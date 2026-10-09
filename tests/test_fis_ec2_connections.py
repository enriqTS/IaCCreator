"""Explicit fault targets remain deterministic, scoped, and template-only."""

import json
import re
from copy import deepcopy

import hcl2
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.fis_ec2 import ec2_fault_preconditions
from app.models.connection_configs.fis_ec2 import FisEc2Config
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_eks_prometheus_connections import evaluate
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
        resolve_spec(ServiceType.FAULT_INJECTION_SIMULATOR, ServiceType.EC2, None, {})
    )


def add_instance(payload, name):
    payload["resources"].append(
        dict(deepcopy(payload["resources"][1]), name=name, id=name)
    )
    payload["connections"].append(
        dict(deepcopy(payload["connections"][0]), target=name, target_id=name)
    )


def policy_expression(tree):
    return re.search(
        r"  policy = (.*?)\n  lifecycle \{", file_with(tree, "/ec2_targets.tf"), re.S
    )[1]


def native_values(count=1):
    instances = {
        f"instance-{index}": {
            "arn": f"arn:aws:ec2:us-east-1:123456789012:instance/i-{index:017x}",
            "can_stop": True,
        }
        for index in range(count)
    }
    return {
        "var.role_arn": "arn:aws:iam::123456789012:role/fis/experiment",
        "var.action_name": "fault_action",
        "var.fis_ec2_targets": instances,
        "var.fis_ec2_action": {"operation": "reboot", "selection_mode": "COUNT(1)"},
        "local.fis_ec2_arns": [instance["arn"] for instance in instances.values()],
        "data.aws_partition.experiment.partition": "aws",
        "data.aws_region.experiment.region": "us-east-1",
        "data.aws_caller_identity.experiment.account_id": "123456789012",
    }


def test_template_uses_explicit_native_targets_and_existing_experiment_role():
    payload = architecture()
    tree = generate(payload)
    template = resources(tree, "aws_fis_experiment_template")[0]
    action = template["action"][0]
    assert action["name"] == "${var.action_name}"
    assert (
        'action_id = "aws:ec2:${var.fis_ec2_action.operation}-instances"'
        in file_with(tree, "/fault-injection-simulator.tf")
    )
    assert action["target"][0]["key"] == "Instances"
    assert action["target"][0]["value"] == "managed_ec2"
    target = template["target"][0]
    assert target["resource_type"] == "aws:ec2:instance"
    assert target["resource_arns"] == "${local.fis_ec2_arns}"
    assert target["selection_mode"] == "${var.fis_ec2_action.selection_mode}"
    assert "resource_tag" not in target and "filter" not in target
    assert "parameter" not in action
    assert template["role_arn"] == "${var.role_arn}"
    assert template["depends_on"] == ["${aws_iam_role_policy.fis_ec2}"]
    assert len(template["lifecycle"][0]["precondition"]) == 6
    assert template["stop_condition"][0]["source"] == "none"
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert policy["name_prefix"] == "fis-ec2-"
    assert policy["role"] == "${data.aws_iam_role.fis_ec2.name}"
    assert len(policy["lifecycle"][0]["precondition"]) == 7
    assert not resources(tree, "aws_iam_role")
    assert not resources(tree, "aws_fis_experiment")
    assert not resources(tree, "aws_kms_grant")
    main = file_with(tree, "/environments/dev/main.tf")
    assert "module.target-resource.fis_instance" in main
    assert 'operation = "reboot"' in main and 'selection_mode = "COUNT(1)"' in main
    outputs = file_with(tree, "/target-resource/outputs.tf")
    assert "aws_instance.target-resource.arn" in outputs
    assert "root_block_device" in outputs and "disable_api_stop" in outputs
    assert "module.source-resource" not in outputs
    result = ConnectionProcessor().process_all(project(payload))
    assert {(item.module, item.filename) for item in result.resources} == {
        ("source-resource", "ec2_targets.tf")
    }
    assert not result.iam


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=5, unique=True),
    operation=st.sampled_from(["reboot", "stop"]),
    duplicate_count=st.integers(1, 3),
)
@settings(max_examples=20, deadline=None)
def test_targets_names_operations_and_duplicates_are_order_independent(
    names, operation, duplicate_count
):
    payload = architecture()
    instance = payload["resources"].pop()
    edge = payload["connections"].pop()
    for name in names:
        payload["resources"].append(
            dict(deepcopy(instance), name=f"target-{name}", id=name)
        )
        payload["connections"].append(
            dict(
                deepcopy(edge),
                target=f"target-{name}",
                target_id=name,
                connection_config={"operation": operation, "selection_mode": "ALL"},
            )
        )
    tree = generate(payload)
    parsed = hcl2.loads(
        file_with(tree, "/environments/dev/main.tf"),
        serialization_options=hcl2.utils.SerializationOptions(strip_string_quotes=True),
    )
    module = next(
        item["source-resource"]
        for item in parsed["module"]
        if "source-resource" in item
    )
    assert set(module["fis_ec2_targets"]) == {f"target-{name}" for name in names}
    assert module["fis_ec2_action"]["operation"] == operation
    assert len(resources(tree, "aws_iam_role_policy")) == 1
    payload["connections"] = list(reversed(payload["connections"] * duplicate_count))
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "config",
    [
        {"operation": "terminate"},
        {"operation": "REBOOT"},
        {"operation": True},
        {"selection_mode": "COUNT(0)"},
        {"selection_mode": "COUNT(6)"},
        {"selection_mode": "PERCENT(100)"},
        {"selection_mode": "ALL "},
        {"selection_mode": None},
        {"start_instances_after_duration": "PT5M"},
        {"unknown": True},
    ],
)
def test_invalid_operations_selection_and_restart_fields_are_rejected(config):
    with pytest.raises(ValidationError):
        FisEc2Config.model_validate(config)
    payload = architecture()
    payload["connections"][0]["connection_config"] = config
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize(
    "role",
    [
        "",
        "experiment",
        "arn:aws:iam::123456789012:user/experiment",
        "arn:aws:sts::123456789012:assumed-role/fis/session",
        "arn:aws:iam::123456789012:role/*",
    ],
)
def test_invalid_roles_fail_generation_and_preview(role):
    payload = architecture()
    payload["resources"][0]["config"]["role_arn"] = role
    with pytest.raises(
        InvalidConnectionConfigError, match="external experiment role ARN"
    ):
        generate(payload)
    with pytest.raises(InvalidConnectionConfigError):
        ConnectionPreviewer().preview_all(project(payload))


@pytest.mark.parametrize(
    "mode", ["operation", "selection", "too_many", "count", "name"]
)
def test_conflicting_and_out_of_bounds_target_bindings_are_rejected(mode):
    payload = architecture()
    if mode in {"operation", "selection"}:
        add_instance(payload, "other-instance")
        payload["connections"][-1]["connection_config"] = (
            {"operation": "stop"} if mode == "operation" else {"selection_mode": "ALL"}
        )
    elif mode == "too_many":
        for index in range(5):
            add_instance(payload, f"other-{index}")
    elif mode == "count":
        payload["connections"][0]["connection_config"] = {"selection_mode": "COUNT(2)"}
    else:
        payload["resources"][0]["config"]["action_name"] = "bad/name"
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_effective_region_validation_checks_all_targets_and_environment_overrides():
    payload = architecture()
    add_instance(payload, "regional-instance")
    payload["resources"][-1]["provider_region"] = "eu-west-1"
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)
    payload["environments"][0]["variables"]["region"] = "eu-central-1"
    assert generate(payload)


def test_connection_owns_action_selection_and_unconnected_generation_is_preserved():
    payload = architecture()
    payload["resources"][0]["config"]["action_id"] = "aws:fis:wait"
    assert "var.action_id" not in file_with(
        generate(payload), "/fault-injection-simulator.tf"
    )
    payload["connections"] = []
    tree = generate(payload)
    template = resources(tree, "aws_fis_experiment_template")[0]
    assert template["action"][0]["action_id"] == "${var.action_id}"
    assert "target" not in template and "depends_on" not in template
    assert not resources(tree, "aws_iam_role_policy")
    assert 'output "fis_instance"' not in file_with(tree, "/target-resource/outputs.tf")


@needs_terraform
@pytest.mark.parametrize("connected", [True, False])
@pytest.mark.parametrize(
    "partition, region", [("aws", "us-east-1"), ("aws-cn", "cn-north-1")]
)
def test_template_arn_uses_native_id_and_deployment_identity(
    tmp_path, connected, partition, region
):
    payload = architecture()
    if not connected:
        payload["connections"] = []
    expression = re.search(
        r'output "template_arn" \{[^}]*?\n\s+value\s+= ([^\n]+)',
        file_with(generate(payload), "/source-resource/outputs.tf"),
    )[1]
    arn = evaluate(
        tmp_path,
        expression,
        {
            "data.aws_partition.experiment.partition": partition,
            "data.aws_region.experiment.region": region,
            "data.aws_caller_identity.experiment.account_id": "123456789012",
            "aws_fis_experiment_template.source-resource.id": "EXT123456789",
        },
    )
    assert (
        arn
        == f"arn:{partition}:fis:{region}:123456789012:experiment-template/EXT123456789"
    )


def test_preview_explains_template_only_execution_and_manual_stop_recovery():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"operation": "stop"}
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert {item.resource_type for item in preview.resources} == {"aws_iam_role_policy"}
    message = " ".join(item.message for item in preview.issues)
    for text in (
        "does not start",
        "fis.amazonaws.com",
        "iam:GetRole",
        "stop/start",
        "leave instances stopped",
        "automatic restart/KMS",
        "source=none",
        "standalone action_id",
    ):
        assert text in message


@needs_terraform
@pytest.mark.parametrize("operation", ["reboot", "stop"])
@pytest.mark.parametrize("count", [1, 5])
def test_actual_emitted_policy_scopes_lifecycle_actions_and_regional_discovery(
    tmp_path, operation, count
):
    values = native_values(count)
    values["var.fis_ec2_action"]["operation"] = operation
    policy = json.loads(
        evaluate(tmp_path, policy_expression(generate(architecture())), values)
    )
    lifecycle, discovery = policy["Statement"]
    assert lifecycle["Resource"] == values["local.fis_ec2_arns"]
    assert set(lifecycle["Action"]) == (
        {"ec2:StopInstances", "ec2:StartInstances"}
        if operation == "stop"
        else {"ec2:RebootInstances"}
    )
    assert discovery == {
        "Effect": "Allow",
        "Action": ["ec2:DescribeInstances"],
        "Resource": "*",
        "Condition": {"StringEquals": {"aws:RequestedRegion": "us-east-1"}},
    }
    assert "kms:" not in json.dumps(
        policy
    ) and "ec2:TerminateInstances" not in json.dumps(policy)


@needs_terraform
@pytest.mark.parametrize(
    "index, mutation",
    [
        (0, {"role_arn": "arn:aws:iam::999999999999:role/fis"}),
        (0, {"role_arn": "arn:aws-cn:iam::123456789012:role/fis"}),
        (0, {"role_arn": "arn:aws:iam::123456789012:role/*"}),
        (1, {"arn": "arn:aws:ec2:us-east-1:123456789012:instance/*"}),
        (1, {"arn": "arn:aws:ec2:eu-west-1:123456789012:instance/i-12345678"}),
        (1, {"arn": "arn:aws:ec2:us-east-1:999999999999:instance/i-12345678"}),
        (1, {"arn": "arn:aws-cn:ec2:us-east-1:123456789012:instance/i-12345678"}),
        (1, {"arn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-12345678"}),
        (3, {"selection_mode": "COUNT(2)"}),
        (3, {"selection_mode": "PERCENT(100)"}),
        (3, {"selection_mode": "COUNT(0)"}),
        (4, {"operation": "terminate"}),
        (4, {"operation": "stop", "can_stop": False}),
        (5, {"action_name": ""}),
        (5, {"action_name": "x" * 65}),
        (5, {"action_name": "bad/name"}),
    ],
)
def test_native_guards_reject_unsafe_module_overrides(tmp_path, index, mutation):
    values = native_values()
    for key, value in mutation.items():
        if key in {"role_arn", "action_name"}:
            values[f"var.{key}"] = value
        elif key in {"operation", "selection_mode"}:
            values["var.fis_ec2_action"][key] = value
        else:
            values["var.fis_ec2_targets"]["instance-0"][key] = value
    assert (
        evaluate(tmp_path, str(ec2_fault_preconditions()[index]["condition"]), values)
        is False
    )


@needs_terraform
@pytest.mark.parametrize("mode", ["empty", "duplicate", "too_many"])
def test_native_target_cardinality_is_checked_before_policy_attachment(tmp_path, mode):
    values = native_values(0 if mode == "empty" else 6 if mode == "too_many" else 2)
    if mode == "duplicate":
        values["local.fis_ec2_arns"][1] = values["local.fis_ec2_arns"][0]
    assert (
        evaluate(tmp_path, str(ec2_fault_preconditions()[2]["condition"]), values)
        is False
    )


@needs_terraform
@pytest.mark.parametrize(
    "operation, count, selection, can_stop",
    [
        ("reboot", 1, "COUNT(1)", False),
        ("stop", 5, "ALL", True),
        ("stop", 5, "COUNT(5)", True),
    ],
)
def test_native_guards_accept_supported_operations_and_selection(
    tmp_path, operation, count, selection, can_stop
):
    values = native_values(count)
    values["var.fis_ec2_action"] = {"operation": operation, "selection_mode": selection}
    for instance in values["var.fis_ec2_targets"].values():
        instance["can_stop"] = can_stop
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in ec2_fault_preconditions())
        + "]"
    )
    assert evaluate(tmp_path, expression, values) == [True] * 6


@needs_terraform
@pytest.mark.parametrize("path", ["fis/", "other/", ""])
def test_policy_guard_compares_full_role_identity(tmp_path, path):
    policy = resources(generate(architecture()), "aws_iam_role_policy")[0]
    condition = policy["lifecycle"][0]["precondition"][-1]["condition"][2:-1]
    values = native_values()
    values["data.aws_iam_role.fis_ec2.arn"] = (
        f"arn:aws:iam::123456789012:role/{path}experiment"
    )
    assert evaluate(tmp_path, condition, values) is (path == "fis/")


@needs_terraform
@pytest.mark.parametrize(
    "ebs_root, protected", [(False, False), (True, False), (True, True)]
)
def test_native_stop_capability_uses_root_storage_and_protection(
    tmp_path, ebs_root, protected
):
    outputs = file_with(generate(architecture()), "/target-resource/outputs.tf")
    parsed = hcl2.loads(
        outputs,
        serialization_options=hcl2.utils.SerializationOptions(strip_string_quotes=True),
    )
    expression = next(
        output["fis_instance"]["value"]
        for output in parsed["output"]
        if "fis_instance" in output
    )
    expression = expression["can_stop"][2:-1]
    value = evaluate(
        tmp_path,
        expression,
        {
            "aws_instance.target-resource.arn": "arn:aws:ec2:us-east-1:123456789012:instance/i-12345678",
            "aws_instance.target-resource.root_block_device": [{}] if ebs_root else [],
            "aws_instance.target-resource.disable_api_stop": protected,
        },
    )
    assert value is (ebs_root and not protected)


@pytest.mark.terraform
@needs_terraform
@pytest.mark.parametrize(
    "mode",
    [
        "reboot",
        "stop",
        "duplicate",
        "all",
        "count",
        "shared_instance",
        "mixed",
        "regional",
        "unconnected",
    ],
)
def test_generated_templates_validate_and_have_acyclic_graphs(tmp_path, mode):
    payload = architecture()
    if mode == "stop":
        payload["connections"][0]["connection_config"] = {"operation": "stop"}
    elif mode == "duplicate":
        payload["connections"].append(deepcopy(payload["connections"][0]))
    elif mode in {"all", "count"}:
        for index in range(4):
            add_instance(payload, f"instance-{index}")
        for edge in payload["connections"]:
            edge["connection_config"] = {
                "selection_mode": "ALL" if mode == "all" else "COUNT(5)"
            }
    elif mode == "shared_instance":
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
    elif mode == "mixed":
        payload = secret_architecture(ServiceType.EC2)
        before = resources(generate(payload), "aws_instance")[0]
        template = architecture()
        payload["resources"].append(
            dict(template["resources"][0], name="experiment", id="experiment")
        )
        payload["connections"].append(
            dict(
                template["connections"][0],
                source="experiment",
                source_id="experiment",
                target="source-resource",
                target_id="src",
            )
        )
        attachment = connection_architecture(
            resolve_spec(ServiceType.EBS, ServiceType.EC2, None, {})
        )
        payload["resources"].append(
            dict(
                attachment["resources"][0], name="attached-volume", id="attached-volume"
            )
        )
        payload["connections"].append(
            dict(
                attachment["connections"][0],
                source="attached-volume",
                source_id="attached-volume",
                target="source-resource",
                target_id="src",
            )
        )
        after = resources(generate(payload), "aws_instance")[0]
        assert before == after
    elif mode == "regional":
        for instance in payload["resources"]:
            instance["provider_region"] = "eu-west-1"
    elif mode == "unconnected":
        payload["connections"] = []
    tree = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    _write_tree(tmp_path, tree)
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
