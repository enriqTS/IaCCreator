"""Workflow logging preserves task composition and separates delivery from stream IAM."""

import json
import re
from copy import deepcopy

import hcl2
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.step_functions_logs import (
    workflow_log_destination,
    workflow_log_policy_preconditions,
    workflow_log_preconditions,
)
from app.models.connection_configs.step_functions_logs import StepFunctionsLogsConfig
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
from tests.test_step_functions_lambda_connections import (
    mixed_architecture as lambda_secret_architecture,
)


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.STEP_FUNCTIONS, ServiceType.CLOUDWATCH, None, {})
    )


def logging_settings(tree):
    parsed = hcl2.loads(
        file_with(tree, "/environments/dev/main.tf"),
        serialization_options=hcl2.utils.SerializationOptions(strip_string_quotes=True),
    )
    return parsed["module"][0]["source-resource"]["workflow_logs"]


def policy_expression(tree):
    return re.search(
        r"  policy = (.*?)\n  lifecycle \{", file_with(tree, "/execution_logs.tf"), re.S
    )[1]


def native_values():
    return {
        "var.role_arn": "arn:aws:iam::123456789012:role/workflows/execution",
        "var.state_machine_type": "STANDARD",
        "var.workflow_logs": {
            "arn": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/vendedlogs/states/application",
            "log_group_class": "STANDARD",
            "level": "ALL",
            "include_execution_data": False,
        },
        "data.aws_partition.workflow_logs.partition": "aws",
        "data.aws_region.workflow_logs.region": "us-east-1",
        "data.aws_caller_identity.workflow_logs.account_id": "123456789012",
    }


def add_logging(payload, target="execution-logs", **config):
    template = architecture()
    group = deepcopy(template["resources"][1])
    group.update(name=target, id=target)
    payload["resources"].append(group)
    payload["connections"].append(
        dict(
            template["connections"][0],
            target=target,
            target_id=target,
            connection_config=config,
        )
    )


def add_key(payload, group="target-resource"):
    template = connection_architecture(
        resolve_spec(ServiceType.KMS, ServiceType.CLOUDWATCH, None, {})
    )
    payload["resources"].append(
        dict(template["resources"][0], name="log-key", id="log-key")
    )
    payload["connections"].append(
        dict(
            template["connections"][0],
            source="log-key",
            source_id="log-key",
            target=group,
            target_id="tgt" if group == "target-resource" else group,
        )
    )


def test_logging_uses_ready_native_group_and_existing_external_role():
    payload = architecture()
    tree = generate(payload)
    machine = resources(tree, "aws_sfn_state_machine")[0]
    assert machine["definition"] == "${var.definition}"
    assert machine["role_arn"] == "${var.role_arn}"
    logging = machine["logging_configuration"][0]
    assert f"log_destination = {workflow_log_destination()}" in file_with(
        tree, "/step-functions.tf"
    )
    assert (
        logging["include_execution_data"]
        == "${var.workflow_logs.include_execution_data}"
    )
    assert logging["level"] == "${var.workflow_logs.level}"
    assert machine["depends_on"] == ["${aws_iam_role_policy.workflow_logs}"]
    assert len(machine["lifecycle"][0]["precondition"]) == 4
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert len(policy["lifecycle"][0]["precondition"]) == 2
    assert policy["role"] == "${data.aws_iam_role.workflow_logs.name}"
    assert 'name = element(reverse(split("/", var.role_arn)), 0)' in file_with(
        tree, "/execution_logs.tf"
    )
    assert policy["name_prefix"] == "execution-logs-"
    for kind in (
        "aws_iam_role",
        "aws_cloudwatch_log_resource_policy",
        "aws_cloudwatch_log_delivery",
    ):
        assert not resources(tree, kind)
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    settings = logging_settings(tree)
    assert settings["arn"] == "${module.target-resource.log_group_arn}"
    assert settings["level"] == "ALL" and settings["include_execution_data"] is False
    contribution = ConnectionProcessor().process_all(project(payload))
    assert {(item.module, item.filename) for item in contribution.resources} == {
        ("source-resource", "execution_logs.tf")
    }
    assert not contribution.iam
    assert "module.source-resource" not in file_with(
        tree, "/target-resource/outputs.tf"
    )


@given(
    level=st.sampled_from(["ALL", "ERROR", "FATAL"]),
    include=st.booleans(),
    count=st.integers(1, 4),
    name=resource_name_st,
)
@settings(max_examples=20, deadline=None)
def test_effective_settings_duplicate_connections_and_names_are_deterministic(
    level, include, count, name
):
    payload = architecture()
    payload["resources"][1]["config"]["log_group_name"] = (
        f"/aws/vendedlogs/states/{name}"
    )
    payload["connections"][0]["connection_config"] = {
        "level": level,
        "include_execution_data": include,
    }
    payload["connections"] *= count
    tree = generate(payload)
    settings = logging_settings(tree)
    assert settings["level"] == level and settings["include_execution_data"] is include
    assert len(resources(tree, "aws_iam_role_policy")) == 1
    assert (
        file_with(tree, "/source-resource/variables.tf").count(
            'variable "workflow_logs"'
        )
        == 1
    )
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "config",
    [
        {"level": "OFF"},
        {"level": "DEBUG"},
        {"level": "all"},
        {"level": ""},
        {"include_execution_data": 1},
        {"include_execution_data": "true"},
        {"include_execution_data": None},
        {"unknown": True},
    ],
)
def test_invalid_logging_settings_fail_model_and_generation(config):
    with pytest.raises(ValidationError):
        StepFunctionsLogsConfig.model_validate(config)
    payload = architecture()
    payload["connections"][0]["connection_config"] = config
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize(
    "role",
    [
        "",
        "execution",
        "arn:aws:sts::123456789012:assumed-role/role/session",
        "arn:aws:iam::123456789012:user/execution",
        "arn:aws:iam::123456789012:role/",
        "arn:aws:iam::123456789012:role/*",
    ],
)
def test_invalid_or_missing_execution_roles_fail_preview_and_generation(role):
    payload = architecture()
    payload["resources"][0]["config"]["role_arn"] = role
    with pytest.raises(InvalidConnectionConfigError, match="execution role ARN"):
        generate(payload)
    with pytest.raises(InvalidConnectionConfigError):
        ConnectionPreviewer().preview_all(project(payload))


@pytest.mark.parametrize("mode", ["two_groups", "level", "payloads"])
def test_conflicting_destinations_or_duplicate_settings_are_rejected(mode):
    payload = architecture()
    connection = deepcopy(payload["connections"][0])
    if mode == "two_groups":
        group = deepcopy(payload["resources"][1])
        group.update(name="other-group", id="other-group")
        payload["resources"].append(group)
        connection.update(target="other-group", target_id="other-group")
    else:
        connection["connection_config"] = (
            {"level": "ERROR"} if mode == "level" else {"include_execution_data": True}
        )
    payload["connections"].append(connection)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_unsupported_workflow_type_and_delivery_only_group_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["state_machine_type"] = "INVALID"
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)
    payload = architecture()
    payload["resources"][1]["config"]["log_group_class"] = "DELIVERY"
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_effective_region_validation_and_environment_overrides():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)
    payload["environments"][0]["variables"]["region"] = "eu-central-1"
    assert "providers =" not in file_with(
        generate(payload), "/environments/dev/main.tf"
    )


def test_unconnected_workflows_keep_logging_unconfigured():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    machine = resources(tree, "aws_sfn_state_machine")[0]
    assert "logging_configuration" not in machine and "depends_on" not in machine
    assert not resources(tree, "aws_iam_role_policy")


def test_preview_explains_unscoped_permissions_and_payload_delivery_limits():
    payload = architecture()
    payload["resources"][1]["config"]["kms_key_id"] = "alias/external-logs"
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert {resource.resource_type for resource in preview.resources} == {
        "aws_iam_role_policy"
    }
    assert not preview.iam
    message = " ".join(issue.message for issue in preview.issues)
    for text in (
        "wildcard resources",
        "Payload logging is off",
        "best effort",
        "truncated",
        "/aws/vendedlogs/states/",
        "external KMS key owner",
    ):
        assert text in message


@needs_terraform
@pytest.mark.parametrize("suffix", ["", ":*"])
def test_actual_policy_scopes_stream_writes_and_has_only_required_management_actions(
    tmp_path, suffix
):
    values = native_values()
    values["var.workflow_logs"]["arn"] += suffix
    policy = json.loads(
        evaluate(tmp_path, policy_expression(generate(architecture())), values)
    )
    management, streams = policy["Statement"]
    assert management["Resource"] == "*"
    assert set(management["Action"]) == {
        "logs:CreateLogDelivery",
        "logs:GetLogDelivery",
        "logs:UpdateLogDelivery",
        "logs:DeleteLogDelivery",
        "logs:ListLogDeliveries",
        "logs:PutResourcePolicy",
        "logs:DescribeResourcePolicies",
        "logs:DescribeLogGroups",
    }
    assert set(streams["Action"]) == {"logs:CreateLogStream", "logs:PutLogEvents"}
    assert (
        streams["Resource"]
        == "arn:aws:logs:us-east-1:123456789012:log-group:/aws/vendedlogs/states/application:log-stream:*"
    )
    assert len(policy["Statement"]) == 2 and policy["Version"] == "2012-10-17"
    assert (
        evaluate(tmp_path, str(workflow_log_destination()), values)
        == "arn:aws:logs:us-east-1:123456789012:log-group:/aws/vendedlogs/states/application:*"
    )


@needs_terraform
@pytest.mark.parametrize(
    "index, mutation",
    [
        (0, {"role_arn": "arn:aws:iam::999999999999:role/workflow"}),
        (0, {"role_arn": "arn:aws-cn:iam::123456789012:role/workflow"}),
        (0, {"role_arn": "arn:aws:iam::123456789012:user/workflow"}),
        (0, {"role_arn": "arn:aws:iam::123456789012:role/*"}),
        (1, {"arn": "not-an-arn"}),
        (1, {"arn": "arn:aws:logs:us-east-1:123456789012:log-group:" + "a" * 256}),
        (
            1,
            {
                "arn": "arn:aws:logs:us-east-1:123456789012:log-group:app:log-stream:stream"
            },
        ),
        (2, {"arn": "arn:aws:logs:eu-west-1:123456789012:log-group:app"}),
        (2, {"arn": "arn:aws:logs:us-east-1:999999999999:log-group:app"}),
        (2, {"arn": "arn:aws-cn:logs:us-east-1:123456789012:log-group:app"}),
        (3, {"level": "OFF"}),
        (3, {"log_group_class": "DELIVERY"}),
        (3, {"state_machine_type": "INVALID"}),
    ],
)
def test_native_guards_reject_unsafe_environment_and_module_overrides(
    tmp_path, index, mutation
):
    values = native_values()
    for key, value in mutation.items():
        if f"var.{key}" in values:
            values[f"var.{key}"] = value
        else:
            values["var.workflow_logs"][key] = value
    assert (
        evaluate(
            tmp_path, str(workflow_log_preconditions()[index]["condition"]), values
        )
        is False
    )


@needs_terraform
@pytest.mark.parametrize(
    "workflow_type, log_class",
    [
        ("STANDARD", "STANDARD"),
        ("EXPRESS", "STANDARD"),
        ("EXPRESS", "INFREQUENT_ACCESS"),
    ],
)
def test_native_guards_accept_supported_delivery_settings(
    tmp_path, workflow_type, log_class
):
    values = native_values()
    values["var.state_machine_type"] = workflow_type
    values["var.workflow_logs"]["log_group_class"] = log_class
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in workflow_log_preconditions())
        + "]"
    )
    assert evaluate(tmp_path, expression, values) == [True] * 4


@needs_terraform
@pytest.mark.parametrize("path", ["workflows/", "other/", ""])
def test_resolved_role_identity_rejects_wrong_paths_before_policy_attachment(
    tmp_path, path
):
    values = native_values()
    values["data.aws_iam_role.workflow_logs.arn"] = (
        f"arn:aws:iam::123456789012:role/{path}execution"
    )
    expression = str(workflow_log_policy_preconditions()[1]["condition"])
    assert evaluate(tmp_path, expression, values) is (path == "workflows/")


TASK_CONNECTIONS = [
    (ServiceType.SECRETS_MANAGER, "reads_secret"),
    (ServiceType.LAMBDA, "invokes"),
    (ServiceType.ECS, "runs_task"),
    (ServiceType.BATCH, "submits_job"),
    (ServiceType.SNS, "publishes"),
    (ServiceType.SQS, "sends_message"),
    (ServiceType.DYNAMODB, "accesses_item"),
    (ServiceType.EVENTBRIDGE, "puts_event"),
]


@pytest.mark.parametrize("target, kind", TASK_CONNECTIONS)
def test_logging_preserves_each_task_generator_definition_guards_and_dependencies(
    target, kind
):
    spec = resolve_spec(ServiceType.STEP_FUNCTIONS, target, kind, {})
    payload = connection_architecture(spec)
    before = resources(generate(payload), "aws_sfn_state_machine")[0]
    add_logging(payload)
    after = resources(generate(payload), "aws_sfn_state_machine")[0]
    assert after["definition"] == before["definition"]
    assert after["depends_on"] == [
        *before["depends_on"],
        "${aws_iam_role_policy.workflow_logs}",
    ]
    assert (
        after["lifecycle"][0]["precondition"][:-4]
        == before["lifecycle"][0]["precondition"]
    )
    tree = generate(payload)
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.terraform
@needs_terraform
@pytest.mark.parametrize(
    "mode",
    [
        "standard",
        "express",
        "infrequent",
        "duplicate",
        "shared_group",
        "shared_role",
        "managed_key",
        "external_key",
        "mixed",
        "regional",
    ],
)
def test_generated_logging_projects_validate_and_have_acyclic_graphs(tmp_path, mode):
    payload = architecture()
    if mode in {"express", "infrequent"}:
        payload["resources"][0]["config"]["state_machine_type"] = "EXPRESS"
        payload["connections"][0]["connection_config"] = {
            "level": "ERROR",
            "include_execution_data": True,
        }
    if mode == "infrequent":
        payload["resources"][1]["config"]["log_group_class"] = "INFREQUENT_ACCESS"
    elif mode == "duplicate":
        payload["connections"].append(deepcopy(payload["connections"][0]))
    elif mode in {"shared_group", "shared_role"}:
        machine = deepcopy(payload["resources"][0])
        machine.update(name="other-workflow", id="other-workflow")
        payload["resources"].append(machine)
        payload["connections"].append(
            dict(
                payload["connections"][0],
                source="other-workflow",
                source_id="other-workflow",
            )
        )
        if mode == "shared_role":
            payload["connections"].pop()
            template = architecture()["resources"][1]
            payload["resources"].append(
                dict(template, name="other-logs", id="other-logs")
            )
            payload["connections"].append(
                dict(
                    payload["connections"][0],
                    source="other-workflow",
                    source_id="other-workflow",
                    target="other-logs",
                    target_id="other-logs",
                )
            )
        assert len(resources(generate(payload), "aws_iam_role_policy")) == 2
    elif mode == "managed_key":
        add_key(payload)
    elif mode == "external_key":
        payload["resources"][1]["config"]["kms_key_id"] = (
            "arn:aws:kms:us-east-1:123456789012:key/12345678-abcd-1234-abcd-123456789012"
        )
    elif mode == "mixed":
        payload = lambda_secret_architecture()
        add_logging(payload)
        add_key(payload, "execution-logs")
        template = connection_architecture(
            resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.CLOUDWATCH, None, {})
        )
        payload["resources"].append(
            dict(template["resources"][0], name="dashboards", id="dashboards")
        )
        payload["connections"].append(
            dict(
                template["connections"][0],
                source="dashboards",
                source_id="dashboards",
                target="execution-logs",
                target_id="execution-logs",
            )
        )
    elif mode == "regional":
        for item in payload["resources"]:
            item["provider_region"] = "eu-west-1"
    tree = generate(payload)
    payload["connections"].reverse()
    assert generate(payload) == tree
    if mode in {"managed_key", "external_key"}:
        assert "kms:" not in file_with(tree, "/execution_logs.tf")
    if mode == "managed_key":
        assert "module.log-key.service_key_arn" in file_with(
            tree, "/environments/dev/main.tf"
        )
        assert "CloudWatchLogsEncryption" in file_with(tree, "/key_policy.tf")
    _write_tree(tmp_path, tree)
    env_dir = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], env_dir.parent
    )
    _run_terraform(["validate", "-no-color"], env_dir.parent)
    _run_terraform(["graph", "-type=plan"], env_dir.parent)
