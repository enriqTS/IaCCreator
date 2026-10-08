"""Active tracing composes with native group filters without dependency cycles."""

import re
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.lambda_xray import lambda_tracing_precondition
from app.generators.xray_filters import (
    lambda_group_filter_expression,
    lambda_group_preconditions,
)
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
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


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.LAMBDA, ServiceType.X_RAY, None, {})
    )


def connect_peer(payload, source, target, kind=None):
    template = connection_architecture(resolve_spec(source, target, kind, {}))
    peer = deepcopy(template["resources"][1 if source == ServiceType.LAMBDA else 0])
    name = peer["service_type"]
    peer.update(name=name, id=name)
    payload["resources"].append(peer)
    connection = dict(template["connections"][0])
    if source == ServiceType.LAMBDA:
        connection.update(target=name, target_id=name)
    else:
        connection.update(source=name, source_id=name)
    payload["connections"].append(connection)


def native_values():
    return {
        "var.xray_lambda_functions": {
            "diagram-node": {
                "arn": "arn:aws:lambda:us-east-1:123456789012:function:checkout",
                "name": "checkout",
            }
        },
        "var.group_name": "Application",
        "var.filter_expression": "responsetime > 5 OR fault",
        "var.notifications_enabled": False,
        "var.insights_enabled": False,
        "data.aws_partition.xray_tracing.partition": "aws",
        "data.aws_region.xray_tracing.region": "us-east-1",
        "data.aws_caller_identity.xray_tracing.account_id": "123456789012",
    }


def test_active_tracing_and_regional_policy_are_source_owned():
    tree = generate(architecture())
    function = resources(tree, "aws_lambda_function")[0]
    assert function["tracing_config"][0]["mode"] == "${var.tracing_mode}"
    assert "${aws_iam_role_policy.source-resource_xray}" in function["depends_on"]
    assert 'default     = "Active"' in file_with(tree, "/source-resource/variables.tf")
    policy = file_with(tree, "/source-resource/xray_tracing.tf")
    assert "aws_iam_role.source-resource_role.id" in policy
    assert "module.target-resource" not in policy
    assert "xray:PutTraceSegments" in policy
    assert "xray:PutTelemetryRecords" in policy
    assert "xray:GetSampling" not in policy
    assert 'Resource = "*"' in policy
    assert '"aws:RequestedRegion" = data.aws_region.lambda_xray.region' in policy
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_iam_role_policy")) == 2
    main = file_with(tree, "/environments/dev/main.tf")
    assert "module.source-resource.function_arn" in main
    assert "module.source-resource.function_name" in main
    assert "module.target-resource.group_arn" not in main
    assert "aws_xray_group.target-resource.filter_expression" in file_with(
        tree, "/target-resource/outputs.tf"
    )


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=5, unique=True),
    duplicate=st.booleans(),
)
@settings(max_examples=20)
def test_shared_group_members_are_deterministic_and_duplicate_safe(names, duplicate):
    payload = architecture()
    source = payload["resources"].pop(0)
    binding = payload["connections"].pop()
    for name in names:
        member = deepcopy(source)
        member.update(name=f"function-{name}", id=f"function-{name}")
        member["config"]["function_name"] = f"native-{name}"
        payload["resources"].append(member)
        payload["connections"].append(
            dict(binding, source=f"function-{name}", source_id=f"function-{name}")
        )
    if duplicate:
        payload["connections"].append(deepcopy(payload["connections"][0]))
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role_policy")) == 2 * len(names)
    assert len(resources(tree, "aws_xray_group")) == 1
    assert (
        file_with(tree, "/target-resource/variables.tf").count(
            'variable "xray_lambda_functions"'
        )
        == 1
    )
    payload["connections"].reverse()
    assert generate(payload) == tree
    for name in names:
        assert f"module.function-{name}.function_arn" in file_with(
            tree, "/environments/dev/main.tf"
        )


def test_one_function_can_belong_to_multiple_groups_with_one_upload_policy():
    payload = architecture()
    group = deepcopy(payload["resources"][1])
    group.update(name="other-group", id="other")
    group["config"]["group_name"] = "Other"
    payload["resources"].append(group)
    payload["connections"].append(
        dict(payload["connections"][0], target="other-group", target_id="other")
    )
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role_policy")) == 2
    assert len(resources(tree, "aws_xray_group")) == 2
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "resource,changes,field",
    [
        (0, {"tracing_mode": "PassThrough"}, "tracing_mode"),
        (0, {"is_layer": True}, "is_layer"),
        (1, {"group_name": "Default"}, "group_name"),
        (1, {"group_name": "bad*group"}, "group_name"),
        (1, {"filter_expression": "  "}, "filter_expression"),
        (1, {"notifications_enabled": True}, "notifications_enabled"),
    ],
)
def test_conflicting_configuration_is_rejected_in_generation_and_preview(
    resource, changes, field
):
    payload = architecture()
    payload["resources"][resource]["config"].update(changes)
    for operation in [
        generate,
        lambda value: ConnectionPreviewer().preview_all(project(value)),
    ]:
        with pytest.raises(InvalidConnectionConfigError, match=field):
            operation(payload)


def test_unconnected_functions_and_groups_preserve_existing_configuration():
    payload = architecture()
    payload["connections"] = []
    payload["resources"][0]["config"]["tracing_mode"] = "PassThrough"
    tree = generate(payload)
    assert not any(path.endswith("/xray_tracing.tf") for path in tree)
    assert len(resources(tree, "aws_iam_role_policy")) == 1
    assert 'default     = "PassThrough"' in file_with(
        tree, "/source-resource/variables.tf"
    )
    assert (
        resources(tree, "aws_xray_group")[0]["filter_expression"]
        == "${var.filter_expression}"
    )


def test_explicit_active_and_insights_settings_are_preserved():
    payload = architecture()
    payload["resources"][0]["config"]["tracing_mode"] = "Active"
    payload["resources"][1]["config"].update(
        insights_enabled=True, notifications_enabled=True
    )
    assert generate(payload)


def test_cross_region_binding_is_rejected():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "us-east-1"
    payload["resources"][1]["provider_region"] = "eu-west-1"
    with pytest.raises(CrossRegionConnectionError):
        project(payload)


def test_preview_explains_sampling_filtering_and_instrumentation():
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    assert preview.connection_type == "traces_to"
    assert any(
        item.resource_type == "aws_iam_role_policy" for item in preview.resources
    )
    message = " ".join(item.message for item in preview.issues)
    for text in [
        "sampling",
        "AND",
        "five seconds",
        "wildcard",
        "published versions",
        "instrumentation",
        "Kafka",
        "isolate readers",
    ]:
        assert text in message


@needs_terraform
@given(names=st.lists(resource_name_st, min_size=1, max_size=4, unique=True))
@settings(max_examples=5, deadline=None)
def test_filter_selects_both_native_segment_types_and_preserves_predicate(names):
    values = native_values()
    members = {
        f"node-{index}": {
            "name": name,
            "arn": f"arn:aws:lambda:us-east-1:123456789012:function:{name}",
        }
        for index, name in enumerate(names)
    }
    values["var.xray_lambda_functions"] = members
    with TemporaryDirectory() as directory:
        actual = evaluate(Path(directory), lambda_group_filter_expression(), values)
    selectors = [
        f'(service(id(name: "{member["name"]}", type: "AWS::Lambda", account.id: "123456789012")) OR service(id(name: "{member["name"]}", type: "AWS::Lambda::Function", account.id: "123456789012")))'
        for member in members.values()
    ]
    assert actual == f"({' OR '.join(selectors)}) AND (responsetime > 5 OR fault)"


@needs_terraform
@pytest.mark.parametrize(
    "mode,failed",
    [
        ("valid", None),
        ("empty", 0),
        ("malformed", 0),
        ("qualified", 0),
        ("name", 0),
        ("account", 1),
        ("region", 1),
        ("partition", 1),
        ("reserved", 2),
        ("blank", 2),
        ("notifications", 3),
    ],
)
def test_native_group_guards_detect_scope_identity_and_settings_overrides(
    tmp_path, mode, failed
):
    values = native_values()
    member = values["var.xray_lambda_functions"]["diagram-node"]
    if mode == "empty":
        values["var.xray_lambda_functions"] = {}
    elif mode == "malformed":
        member["arn"] = "not-an-arn"
    elif mode == "qualified":
        member["arn"] += ":live"
    elif mode == "name":
        member["name"] = "different"
    elif mode in {"account", "region", "partition"}:
        key = {
            "account": "data.aws_caller_identity.xray_tracing.account_id",
            "region": "data.aws_region.xray_tracing.region",
            "partition": "data.aws_partition.xray_tracing.partition",
        }[mode]
        values[key] = {
            "account": "999999999999",
            "region": "eu-west-1",
            "partition": "aws-cn",
        }[mode]
    elif mode == "reserved":
        values["var.group_name"] = "Default"
    elif mode == "blank":
        values["var.filter_expression"] = " "
    elif mode == "notifications":
        values["var.notifications_enabled"] = True
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in lambda_group_preconditions())
        + "]"
    )
    actual = evaluate(tmp_path, expression, values)
    if mode == "malformed":
        assert actual == [False, False, True, True]
    else:
        assert actual == [index != failed for index in range(4)]


@needs_terraform
@pytest.mark.parametrize("mode,expected", [("Active", True), ("PassThrough", False)])
def test_function_precondition_rejects_native_mode_overrides(tmp_path, mode, expected):
    assert (
        evaluate(
            tmp_path,
            lambda_tracing_precondition()["condition"],
            {"var.tracing_mode": mode},
        )
        is expected
    )


@needs_terraform
def test_upload_policy_uses_only_the_function_region(tmp_path):
    content = file_with(generate(architecture()), "/source-resource/xray_tracing.tf")
    expression = re.search(r"policy = jsonencode\(([\s\S]+)\)\n}", content)[1]
    policy = evaluate(
        tmp_path, expression, {"data.aws_region.lambda_xray.region": "eu-west-1"}
    )
    assert policy["Statement"] == [
        {
            "Effect": "Allow",
            "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
            "Resource": "*",
            "Condition": {"StringEquals": {"aws:RequestedRegion": "eu-west-1"}},
        }
    ]


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode", ["plain", "shared_group", "multiple_groups", "mixed", "regional"]
)
def test_generated_projects_validate_and_have_acyclic_graphs(tmp_path, mode):
    payload = architecture()
    if mode == "shared_group":
        source = deepcopy(payload["resources"][0])
        source.update(name="other-function", id="other")
        source["config"]["function_name"] = "OtherFunction"
        payload["resources"].append(source)
        payload["connections"].append(
            dict(payload["connections"][0], source="other-function", source_id="other")
        )
    elif mode == "multiple_groups":
        target = deepcopy(payload["resources"][1])
        target.update(name="other-group", id="other")
        target["config"]["group_name"] = "OtherGroup"
        payload["resources"].append(target)
        payload["connections"].append(
            dict(payload["connections"][0], target="other-group", target_id="other")
        )
    elif mode == "mixed":
        connect_peer(payload, ServiceType.LAMBDA, ServiceType.CLOUDWATCH)
        connect_peer(payload, ServiceType.LAMBDA, ServiceType.SQS, "dead_letters_to")
        connect_peer(payload, ServiceType.LAMBDA, ServiceType.SECRETS_MANAGER)
        connect_peer(payload, ServiceType.MANAGED_GRAFANA, ServiceType.X_RAY)
    elif mode == "regional":
        for resource in payload["resources"]:
            resource["provider_region"] = "eu-west-1"
    tree = generate(payload)
    if mode == "mixed":
        function = resources(tree, "aws_lambda_function")[0]
        assert len(function["lifecycle"][0]["precondition"]) == 2
        assert "logging_config" in function and "dead_letter_config" in function
        assert "aws_xray_group.target-resource.filter_expression" in file_with(
            tree, "/target-resource/outputs.tf"
        )
        assert "module.target-resource.grafana_group_filter" in file_with(
            tree, "/environments/dev/main.tf"
        )
        assert "secretsmanager:GetSecretValue" in file_with(
            tree, "/source-resource/runtime_secrets_policy.tf"
        )
    payload["connections"].reverse()
    assert generate(payload) == tree
    _write_tree(tmp_path, tree)
    path = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], path.parent
    )
    _run_terraform(["validate", "-no-color"], path.parent)
    _run_terraform(["graph", "-type=plan"], path.parent)
