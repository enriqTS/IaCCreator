"""Application logs preserve container composition and execution-role ownership."""

import json
import re
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.ecs_logs import ecs_log_preconditions, render_ecs_log_resources
from app.models.connection_configs.ecs_logs import EcsLogsConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_ecs_xray_connections import mixed_architecture as tracing_architecture
from tests.test_eks_prometheus_connections import evaluate
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.ECS, ServiceType.CLOUDWATCH, "logs_to", {})
    )


def mixed_architecture(*, encrypted=False):
    payload = tracing_architecture()
    payload["resources"][0]["config"]["ecs_memory"] = "1024"
    template = architecture()
    group = template["resources"][1]
    group.update(name="application-logs", id="application-logs")
    payload["resources"].append(group)
    payload["connections"].append(
        dict(
            template["connections"][0],
            target="application-logs",
            target_id="application-logs",
        )
    )
    query = connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.CLOUDWATCH, "queries", {})
    )
    payload["connections"].append(
        dict(
            query["connections"][0],
            source="managed-grafana",
            source_id="managed-grafana",
            target="application-logs",
            target_id="application-logs",
        )
    )
    if encrypted:
        template = connection_architecture(
            resolve_spec(ServiceType.KMS, ServiceType.CLOUDWATCH, "encrypts", {})
        )
        key = template["resources"][0]
        key.update(name="log-key", id="log-key")
        payload["resources"].append(key)
        payload["connections"].append(
            dict(
                template["connections"][0],
                source="log-key",
                source_id="log-key",
                target="application-logs",
                target_id="application-logs",
            )
        )
    return payload


def append_binding(payload, container_name, *, target=None, **settings):
    connection = deepcopy(payload["connections"][0])
    connection["connection_config"] = {"container_name": container_name, **settings}
    if target:
        connection.update(target=target, target_id=target)
    payload["connections"].append(connection)


def native_values():
    return {
        "var.ecs_logs": {
            "source-resource": {
                "arn": "arn:aws:logs:us-east-1:123456789012:log-group:/native/app:*",
                "stream_prefix": "ecs",
                "mode": "non-blocking",
                "buffer_size_mib": 10,
            }
        },
        "var.container_definitions": json.dumps(
            [{"name": "source-resource", "image": "app", "cpu": 64, "memory": 256}]
        ),
        "var.ecs_launch_type": "FARGATE",
        "var.subnet_ids": ["subnet-12345678"],
        "var.security_group_ids": ["sg-12345678"],
        "var.ecs_memory": "512",
        "data.aws_partition.ecs_logs.partition": "aws",
        "data.aws_region.ecs_logs.region": "us-east-1",
        "data.aws_caller_identity.ecs_logs.account_id": "123456789012",
    }


def configuration_expression():
    return re.search(
        r"application_log_configurations = ([\s\S]+)\n}\n", render_ecs_log_resources()
    )[1]


def task_expression(tree):
    content = next(
        content
        for content in tree.values()
        if 'resource "aws_ecs_task_definition"' in content
    )
    return re.search(
        r"\n  container_definitions = (.*?)\n  cpu = var\.ecs_cpu", content, re.S
    )[1]


def test_logging_uses_existing_execution_role_without_attaching_application_credentials():
    payload = architecture()
    tree = generate(payload)
    task = resources(tree, "aws_ecs_task_definition")[0]
    assert task["execution_role_arn"] == "${aws_iam_role.source-resource_role.arn}"
    assert "task_role_arn" not in task
    assert task["depends_on"] == ["${aws_iam_role_policy.source-resource_policy}"]
    assert len(task["lifecycle"][0]["precondition"]) == 7
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_iam_role_policy")) == 1
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    policy = json.loads(file_with(tree, "/iam-policies/source-resource-policy.json"))
    assert len(policy["Statement"]) == 1
    assert policy["Statement"][0]["Resource"] == "*"
    assert "logs:CreateLogStream" in policy["Statement"][0]["Action"]
    assert "logs:PutLogEvents" in policy["Statement"][0]["Action"]
    assert "logs:CreateLogGroup" not in policy["Statement"][0]["Action"]
    assert "module.target-resource.log_group_arn" in file_with(
        tree, "/environments/dev/main.tf"
    )
    assert "module.source-resource" not in file_with(
        tree, "/target-resource/outputs.tf"
    )
    contribution = ConnectionProcessor().process_all(project(payload))
    assert {(item.module, item.filename) for item in contribution.resources} == {
        ("source-resource", "application_logs.tf")
    }
    assert len(contribution.inputs) == 1 and not contribution.iam


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=5, unique=True),
    duplicate=st.booleans(),
)
@settings(max_examples=20, deadline=None)
def test_shared_destinations_and_container_bindings_are_duplicate_and_order_independent(
    names, duplicate
):
    payload = architecture()
    binding = payload["connections"].pop()
    payload["connections"] = [
        dict(deepcopy(binding), connection_config={"container_name": name})
        for name in names
    ]
    if duplicate:
        payload["connections"].append(deepcopy(payload["connections"][0]))
    tree = generate(payload)
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    assert (
        file_with(tree, "/source-resource/variables.tf").count('variable "ecs_logs"')
        == 1
    )
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_distinct_containers_can_use_separate_destinations():
    payload = architecture()
    group = deepcopy(payload["resources"][1])
    group.update(name="other-logs", id="other-logs")
    payload["resources"].append(group)
    append_binding(payload, "worker", target="other-logs", stream_prefix="workers")
    tree = generate(payload)
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 2
    assert "module.other-logs.log_group_arn" in file_with(
        tree, "/environments/dev/main.tf"
    )
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "settings",
    [{"stream_prefix": "other"}, {"mode": "blocking"}, {"buffer_size_mib": 20}],
)
def test_conflicting_container_settings_are_rejected_in_generation_and_preview(
    settings,
):
    payload = architecture()
    append_binding(payload, "source-resource", **settings)
    for operation in (
        generate,
        lambda value: ConnectionPreviewer().preview_all(project(value)),
    ):
        with pytest.raises(InvalidConnectionConfigError, match="only one"):
            operation(payload)


def test_one_container_cannot_use_two_destinations():
    payload = architecture()
    group = deepcopy(payload["resources"][1])
    group.update(name="other-logs", id="other-logs")
    payload["resources"].append(group)
    append_binding(payload, "source-resource", target="other-logs")
    with pytest.raises(InvalidConnectionConfigError, match="only one"):
        generate(payload)


@pytest.mark.parametrize(
    "changes,field",
    [
        ({"subnet_ids": []}, "subnet_ids"),
        ({"security_group_ids": []}, "security_group_ids"),
        ({"ecs_launch_type": "EC2"}, "ecs_launch_type"),
    ],
)
def test_launch_and_network_prerequisites_are_rejected(changes, field):
    payload = architecture()
    payload["resources"][0]["config"].update(changes)
    for operation in (
        generate,
        lambda value: ConnectionPreviewer().preview_all(project(value)),
    ):
        with pytest.raises(InvalidConnectionConfigError, match=field):
            operation(payload)


@pytest.mark.parametrize(
    "container", ["iac-xray-collector", "iac-prometheus-collector"]
)
def test_collectors_cannot_receive_application_log_bindings(container):
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"container_name": container}
    with pytest.raises(InvalidConnectionConfigError, match="diagnostic"):
        generate(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("container_name", "bad/name"),
        ("container_name", "x" * 256),
        ("stream_prefix", ""),
        ("stream_prefix", "bad:prefix"),
        ("stream_prefix", "x" * 129),
        ("mode", "unknown"),
        ("buffer_size_mib", 0),
        ("buffer_size_mib", 65),
        ("buffer_size_mib", 1.5),
        ("buffer_size_mib", True),
    ],
)
def test_typed_settings_reject_invalid_values(field, value):
    with pytest.raises(ValidationError):
        EcsLogsConfig.model_validate({field: value})


def test_region_checks_respect_effective_environment_region():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    for operation in (
        generate,
        lambda value: ConnectionPreviewer().preview_all(project(value)),
    ):
        with pytest.raises(CrossRegionConnectionError):
            operation(payload)
    payload["environments"][0]["variables"] = {"region": "eu-west-1"}
    assert resources(generate(payload), "aws_ecs_task_definition")


def test_blocking_buffers_are_normalized_and_duplicate_safe():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"mode": "blocking"}
    append_binding(payload, "source-resource", mode="blocking", buffer_size_mib=64)
    contribution = ConnectionProcessor().process_all(project(payload))
    assert "buffer_size_mib = 0" in contribution.inputs[0].value
    assert len(contribution.inputs) == 1


def test_preview_reports_delivery_tradeoffs_and_external_encryption():
    payload = architecture()
    payload["resources"][1]["config"]["kms_key_id"] = (
        "arn:aws:kms:us-east-1:123456789012:key/external"
    )
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    text = " ".join(issue.message for issue in preview.issues)
    assert "wildcard" in text and "drop logs" in text and "stall" in text
    assert "external KMS key owner" in text
    assert not preview.iam


def test_unconnected_tasks_keep_existing_configuration():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    assert "execution_role_arn" not in resources(tree, "aws_ecs_task_definition")[0]
    assert not any(path.endswith("/application_logs.tf") for path in tree)


@pytest.mark.parametrize("managed", [False, True])
@needs_terraform
@pytest.mark.terraform
def test_encrypted_log_caller_permissions_have_exact_key_service_and_context(
    tmp_path, managed
):
    payload = architecture()
    if managed:
        template = connection_architecture(
            resolve_spec(ServiceType.KMS, ServiceType.CLOUDWATCH, "encrypts", {})
        )
        key = template["resources"][0]
        key.update(name="log-key", id="log-key")
        payload["resources"].append(key)
        payload["connections"].append(
            dict(template["connections"][0], source="log-key", source_id="log-key")
        )
    else:
        payload["resources"][1]["config"]["kms_key_id"] = "alias/application-logs"
    tree = generate(payload)
    task = resources(tree, "aws_ecs_task_definition")[0]
    assert "task_role_arn" not in task
    assert (
        "${aws_iam_role_policy.source-resource_application_logs}" in task["depends_on"]
    )
    content = file_with(tree, "/source-resource/application_log_encryption.tf")
    expression = re.search(r"policy = jsonencode\(([\s\S]+)\)\n}", content)[1]
    values = native_values()
    values.update(
        {
            "var.kms_access_target-resource_arn"
            if managed
            else "data.aws_kms_key.kms_access_target-resource_arn.arn": "arn:aws:kms:us-east-1:123456789012:key/native-key",
            "data.aws_partition.ecs_logs.dns_suffix": "amazonaws.com",
        }
    )
    statements = evaluate(tmp_path, expression, values)["Statement"]
    statement = statements[0]
    assert set(statement["Action"]) == {
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
    }
    assert statement["Resource"] == [
        "arn:aws:kms:us-east-1:123456789012:key/native-key"
    ]
    assert statement["Condition"] == {
        "StringEquals": {
            "kms:ViaService": "logs.us-east-1.amazonaws.com",
            "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:us-east-1:123456789012:log-group:/native/app",
        }
    }
    assert len(statements) == 2
    assert statements[1] == {
        "Effect": "Allow",
        "Action": ["kms:DescribeKey"],
        "Resource": statement["Resource"],
        "Condition": {
            "StringEquals": {"kms:ViaService": "logs.us-east-1.amazonaws.com"}
        },
    }
    if not managed:
        assert (
            resources(tree, "aws_iam_role_policy")[-1]["role"]
            == "${aws_iam_role.source-resource_role.id}"
        )
        assert 'data "aws_kms_key"' in file_with(
            tree, "/source-resource/kms_access_target-resource_arn.tf"
        )
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_secret_policy_dependency_is_preserved_with_encrypted_execution_logs():
    payload = architecture()
    payload["resources"][1]["config"]["kms_key_id"] = "alias/application-logs"
    template = connection_architecture(
        resolve_spec(ServiceType.ECS, ServiceType.SECRETS_MANAGER, "injects_secret", {})
    )
    secret = template["resources"][1]
    secret.update(name="application-secret", id="application-secret")
    payload["resources"].append(secret)
    payload["connections"].append(
        dict(
            template["connections"][0],
            target="application-secret",
            target_id="application-secret",
        )
    )
    task = resources(generate(payload), "aws_ecs_task_definition")[0]
    assert "task_role_arn" not in task
    assert set(task["depends_on"]) == {
        "${aws_iam_role_policy.source-resource_policy}",
        "${aws_iam_role_policy.runtime_secrets}",
        "${aws_iam_role_policy.source-resource_application_logs}",
    }


def test_shared_encrypted_group_creates_one_execution_key_policy():
    payload = architecture()
    payload["resources"][1]["config"]["kms_key_id"] = "alias/application-logs"
    append_binding(payload, "worker")
    payload["connections"].append(deepcopy(payload["connections"][0]))
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role_policy")) == 2
    content = file_with(tree, "/source-resource/application_log_encryption.tf")
    assert content.count('"kms:ViaService"') == 2
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_secrets_efs_collectors_grafana_and_managed_encryption_compose():
    payload = mixed_architecture(encrypted=True)
    tree = generate(payload)
    task = resources(tree, "aws_ecs_task_definition")[0]
    assert task["execution_role_arn"] == task["task_role_arn"]
    assert "${aws_iam_role_policy.runtime_secrets}" in task["depends_on"]
    assert "${aws_iam_role_policy.source-resource_xray}" in task["depends_on"]
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 3
    assert len(resources(tree, "aws_kms_key")) == 1
    assert "CloudWatchLogsEncryption" in file_with(tree, "/log-key/key_policy.tf")
    payload["connections"].reverse()
    assert generate(payload) == tree


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize("mode", ["non-blocking", "blocking"])
def test_native_driver_options_use_group_identity_and_explicit_delivery_mode(
    tmp_path, mode
):
    values = native_values()
    binding = values["var.ecs_logs"]["source-resource"]
    binding.update(mode=mode, buffer_size_mib=10 if mode == "non-blocking" else 0)
    configurations = evaluate(tmp_path, configuration_expression(), values)
    expected = {
        "awslogs-group": "/native/app",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs",
        "awslogs-create-group": "false",
        "mode": mode,
    }
    if mode == "non-blocking":
        expected["max-buffer-size"] = "10m"
    assert configurations["source-resource"] == {
        "logDriver": "awslogs",
        "options": expected,
    }


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "case,index",
    [
        ("missing_container", 0),
        ("duplicate_container", 0),
        ("empty_bindings", 0),
        ("manual_logging", 1),
        ("invalid_logging", 1),
        ("bad_arn", 2),
        ("region", 3),
        ("partition", 3),
        ("account", 3),
        ("bad_prefix", 4),
        ("mode", 4),
        ("buffer", 4),
        ("fractional_buffer", 4),
        ("launch", 5),
        ("subnets", 5),
        ("security_groups", 5),
        ("capacity", 6),
    ],
)
def test_native_guards_reject_unsafe_module_overrides(tmp_path, case, index):
    values = native_values()
    binding = values["var.ecs_logs"]["source-resource"]
    containers = json.loads(values["var.container_definitions"])
    if case == "missing_container":
        containers[0]["name"] = "other"
    elif case == "duplicate_container":
        containers.append(deepcopy(containers[0]))
        values["var.ecs_memory"] = "1024"
    elif case == "empty_bindings":
        values["var.ecs_logs"] = {}
    elif case in {"manual_logging", "invalid_logging"}:
        containers[0]["logConfiguration"] = (
            {"logDriver": "awsfirelens"} if case == "manual_logging" else "invalid"
        )
    elif case == "bad_arn":
        binding["arn"] = "invalid"
    elif case in {"region", "partition", "account"}:
        binding["arn"] = binding["arn"].replace(
            {"region": "us-east-1", "partition": "arn:aws:", "account": "123456789012"}[
                case
            ],
            {
                "region": "eu-west-1",
                "partition": "arn:aws-cn:",
                "account": "999999999999",
            }[case],
        )
    elif case == "bad_prefix":
        binding["stream_prefix"] = "bad:prefix"
    elif case == "mode":
        binding["mode"] = "unknown"
    elif case in {"buffer", "fractional_buffer"}:
        binding["buffer_size_mib"] = 65 if case == "buffer" else 1.5
    elif case == "launch":
        values["var.ecs_launch_type"] = "EC2"
    elif case in {"subnets", "security_groups"}:
        values[
            f"var.{'subnet_ids' if case == 'subnets' else 'security_group_ids'}"
        ] = []
    elif case == "capacity":
        values["var.ecs_memory"] = "256"
    values["var.container_definitions"] = json.dumps(containers)
    expression = (
        "[" + ", ".join(guard["condition"] for guard in ecs_log_preconditions(0)) + "]"
    )
    result = evaluate(tmp_path, expression, values)
    assert result[index] is False


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize("logging", [None, {}])
def test_empty_logging_configuration_can_receive_managed_settings(tmp_path, logging):
    values = native_values()
    containers = json.loads(values["var.container_definitions"])
    containers[0]["logConfiguration"] = logging
    values["var.container_definitions"] = json.dumps(containers)
    assert evaluate(tmp_path, ecs_log_preconditions(0)[1]["condition"], values) is True


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "collectors,mode,memory,expected",
    [
        (0, "non-blocking", 265, False),
        (0, "non-blocking", 266, True),
        (0, "blocking", 256, True),
        (1, "non-blocking", 512, False),
        (1, "non-blocking", 522, True),
        (2, "non-blocking", 768, False),
        (2, "non-blocking", 778, True),
    ],
)
def test_task_memory_includes_collectors_and_log_buffers(
    tmp_path, collectors, mode, memory, expected
):
    values = native_values()
    values["var.ecs_memory"] = str(memory)
    values["var.ecs_logs"]["source-resource"].update(
        mode=mode, buffer_size_mib=10 if mode == "non-blocking" else 0
    )
    assert (
        evaluate(tmp_path, ecs_log_preconditions(collectors)[6]["condition"], values)
        is expected
    )


@needs_terraform
@pytest.mark.terraform
@given(marker=st.text(alphabet='abcXYZ012${}%\\"é', max_size=25))
@settings(max_examples=6, deadline=None)
def test_serialized_containers_preserve_selected_and_unselected_properties(marker):
    tree = generate(architecture())
    containers = [
        {
            "name": "source-resource",
            "image": "app",
            "environment": [{"name": "KEEP", "value": marker}],
            "secrets": [{"name": "OLD", "valueFrom": "external"}],
            "mountPoints": [
                {
                    "sourceVolume": "external",
                    "containerPath": "/other",
                    "readOnly": False,
                }
            ],
            "portMappings": [{"containerPort": 8000}],
        },
        {
            "name": "worker",
            "image": "worker",
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "external",
                    "awslogs-region": "us-west-2",
                    "awslogs-stream-prefix": "original",
                },
            },
        },
    ]
    values = native_values()
    values["var.container_definitions"] = json.dumps(containers)
    with TemporaryDirectory() as directory:
        values["local.application_log_configurations"] = evaluate(
            Path(directory), configuration_expression(), values
        )
        result = json.loads(evaluate(Path(directory), task_expression(tree), values))
    expected = deepcopy(containers)
    expected[0]["logConfiguration"] = values["local.application_log_configurations"][
        "source-resource"
    ]
    assert result == expected


@needs_terraform
@pytest.mark.terraform
def test_collectors_keep_their_own_logs_and_application_secrets_stay_in_application(
    tmp_path,
):
    tree = generate(mixed_architecture())
    values = native_values()
    values.update(
        {
            "local.runtime_secrets": [
                {
                    "container": "source-resource",
                    "name": "SECRET",
                    "valueFrom": "managed-secret",
                }
            ],
            "local.efs_mounts": [
                {
                    "container": "source-resource",
                    "name": "efs-volume",
                    "path": "/mnt/efs",
                    "read_only": False,
                }
            ],
            "local.xray_collector_configuration": "traces",
            "local.prometheus_collector_configuration": "metrics",
            "aws_cloudwatch_log_group.source-resource_xray.name": "/collector/traces",
            "aws_cloudwatch_log_group.source-resource_prometheus.name": "/collector/metrics",
            "data.aws_region.ecs_xray.region": "us-east-1",
            "data.aws_region.ecs_prometheus.region": "us-east-1",
        }
    )
    values["local.application_log_configurations"] = evaluate(
        tmp_path, configuration_expression(), values
    )
    result = json.loads(evaluate(tmp_path, task_expression(tree), values))
    assert len(result) == 3
    assert result[0]["logConfiguration"]["options"]["awslogs-group"] == "/native/app"
    assert result[0]["secrets"][0]["valueFrom"] == "managed-secret"
    assert result[0]["mountPoints"][0]["sourceVolume"] == "efs-volume"
    for container, group in zip(
        result[1:], ["/collector/traces", "/collector/metrics"], strict=True
    ):
        assert container["logConfiguration"]["options"]["awslogs-group"] == group
        assert not container.get("secrets") and not container.get("mountPoints")


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode",
    [
        "plain",
        "blocking",
        "multiple",
        "shared",
        "mixed",
        "managed_key",
        "external_key",
        "regional",
    ],
)
def test_generated_projects_validate_and_have_acyclic_graphs(tmp_path, mode):
    payload = (
        mixed_architecture(encrypted=mode == "managed_key")
        if mode in {"mixed", "managed_key"}
        else architecture()
    )
    if mode == "blocking":
        payload["connections"][0]["connection_config"] = {"mode": "blocking"}
    if mode == "multiple":
        append_binding(payload, "worker")
    if mode == "shared":
        source = deepcopy(payload["resources"][0])
        source.update(name="other-task", id="other-task")
        payload["resources"].append(source)
        payload["connections"].append(
            dict(payload["connections"][0], source="other-task", source_id="other-task")
        )
    if mode == "external_key":
        payload["resources"][1]["config"]["kms_key_id"] = (
            "arn:aws:kms:us-east-1:123456789012:key/external"
        )
    if mode == "regional":
        for resource in payload["resources"]:
            resource["provider_region"] = "eu-west-1"
    tree = generate(payload)
    _write_tree(tmp_path, tree)
    path = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], path.parent
    )
    _run_terraform(["validate"], path.parent)
    _run_terraform(["graph", "-type=plan"], path.parent)
