"""Managed HTTP stage logs preserve ownership, native scope, and shared destinations."""

from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.api_gateway.access_logs import access_log_preconditions
from app.generators.hcl_renderer import HCLRenderer
from app.models.connection_configs.api_gateway_logs import (
    DEFAULT_ACCESS_LOG_FORMAT,
    ApiGatewayLogsConfig,
)
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from tests.conftest import dns_label_st
from tests.generator_helpers import connection_architecture
from tests.test_api_gateway_certificate_connections import (
    architecture as certificate_architecture,
)
from tests.test_api_gateway_certificate_connections import compose_cognito_lambda
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
        resolve_spec(ServiceType.API_GATEWAY, ServiceType.CLOUDWATCH, "logs_to", {})
    )


def append_binding(
    payload, stage_name, target=None, log_format=DEFAULT_ACCESS_LOG_FORMAT
):
    connection = deepcopy(payload["connections"][0])
    connection["connection_config"] = {
        "stage_name": stage_name,
        "log_format": log_format,
    }
    if target:
        connection.update(target=target, target_id=target)
    payload["connections"].append(connection)


def mixed_architecture(encrypted=False):
    payload = certificate_architecture()
    compose_cognito_lambda(payload)
    logging = architecture()
    group = logging["resources"][1]
    group.update(name="access-logs", id="access-logs")
    payload["resources"].append(group)
    binding = logging["connections"][0]
    binding.update(
        source="target-resource",
        source_id="tgt",
        target="access-logs",
        target_id="access-logs",
    )
    payload["connections"].append(binding)
    for service, kind in [
        (ServiceType.MANAGED_GRAFANA, "queries"),
        *([(ServiceType.KMS, "encrypts")] if encrypted else []),
    ]:
        template = connection_architecture(
            resolve_spec(service, ServiceType.CLOUDWATCH, kind, {})
        )
        source = template["resources"][0]
        name = service.value
        source.update(name=name, id=name)
        payload["resources"].append(source)
        connection = template["connections"][0]
        connection.update(
            source=name, source_id=name, target="access-logs", target_id="access-logs"
        )
        payload["connections"].append(connection)
    return payload


def test_default_stage_consumes_native_group_without_account_or_policy_ownership():
    payload = architecture()
    tree = generate(payload)
    stage = resources(tree, "aws_apigatewayv2_stage")[0]
    assert stage["name"] == "$default"
    assert stage["auto_deploy"] is True
    settings = stage["access_log_settings"][0]
    assert "var.api_access_logs" in settings["destination_arn"]
    assert "trimsuffix" in settings["destination_arn"]
    assert "var.api_access_logs" in settings["format"]
    assert len(stage["lifecycle"][0]["precondition"]) == 3
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    for kind in (
        "aws_api_gateway_account",
        "aws_cloudwatch_log_resource_policy",
        "aws_iam_role",
        "aws_iam_role_policy",
    ):
        assert not resources(tree, kind)
    assert "module.target-resource.log_group_arn" in file_with(
        tree, "/environments/dev/main.tf"
    )
    assert "module.source-resource" not in file_with(
        tree, "/cloudwatch/target-resource/outputs.tf"
    )
    contribution = ConnectionProcessor().process_all(project(payload))
    assert len(contribution.inputs) == 1
    assert (
        contribution.inputs[0].type == "map(object({ arn = string, format = string }))"
    )
    assert {(item.module, item.filename) for item in contribution.resources} == {
        ("source-resource", "access_logs.tf")
    }
    assert not contribution.iam


@given(names=st.lists(dns_label_st, min_size=1, max_size=5), duplicate=st.booleans())
@settings(max_examples=15, deadline=None)
def test_stage_bindings_are_deterministic_shared_and_duplicate_safe(names, duplicate):
    payload = architecture()
    names = [f"stage_{index}_{name}" for index, name in enumerate(names)]
    payload["resources"][0]["config"]["stages"] = [
        {"name": name, "auto_deploy": True} for name in names
    ]
    payload["connections"] = [
        dict(payload["connections"][0], connection_config={"stage_name": name})
        for name in names
    ]
    if duplicate:
        payload["connections"].append(deepcopy(payload["connections"][0]))
    tree = generate(payload)
    assert len(resources(tree, "aws_apigatewayv2_stage")) == len(names)
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    assert (
        file_with(tree, "/source-resource/variables.tf").count(
            'variable "api_access_logs"'
        )
        == 1
    )
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_only_selected_stage_changes_and_deployment_settings_are_preserved():
    payload = architecture()
    payload["resources"][0]["config"]["stages"] = [
        {"name": "qa", "auto_deploy": True, "access_logging_enabled": True},
        {
            "name": "prod",
            "stage_variables": {"release": "v1"},
            "throttling_burst_limit": 20,
            "route_throttling": [{"route_key": "GET /orders", "burst": 5}],
        },
    ]
    payload["connections"][0]["connection_config"] = {"stage_name": "prod"}
    before = deepcopy(payload)
    before["connections"] = []
    tree = generate(payload)
    old = {
        stage["name"]: stage
        for stage in resources(generate(before), "aws_apigatewayv2_stage")
    }
    stages = {
        stage["name"]: stage for stage in resources(tree, "aws_apigatewayv2_stage")
    }
    assert stages["qa"] == old["qa"]
    assert {
        key: value
        for key, value in stages["prod"].items()
        if key not in {"access_log_settings", "lifecycle"}
    } == old["prod"]
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 2


def test_shared_group_has_no_reverse_api_dependency():
    payload = architecture()
    api = deepcopy(payload["resources"][0])
    api.update(name="second-api", id="second-api")
    api["config"]["api_name"] = "second-api"
    payload["resources"].append(api)
    payload["connections"].append(
        dict(payload["connections"][0], source="second-api", source_id="second-api")
    )
    tree = generate(payload)
    assert len(resources(tree, "aws_apigatewayv2_stage")) == 2
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_multiple_destinations_belong_to_distinct_stages():
    payload = architecture()
    payload["resources"][0]["config"]["stages"] = [
        {"name": "qa", "auto_deploy": True},
        {"name": "prod", "auto_deploy": True},
    ]
    payload["connections"][0]["connection_config"] = {"stage_name": "qa"}
    group = deepcopy(payload["resources"][1])
    group.update(name="production-logs", id="production-logs")
    group["config"]["log_group_name"] = "/prod/access"
    payload["resources"].append(group)
    append_binding(payload, "prod", "production-logs")
    tree = generate(payload)
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 2
    assert "module.production-logs.log_group_arn" in file_with(
        tree, "/environments/dev/main.tf"
    )
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "changes,field",
    [
        (
            {
                "protocol_type": "WEBSOCKET",
                "route_selection_expression": "$request.body.action",
                "stages": [{"name": "prod"}],
            },
            "protocol_type",
        ),
        ({"stages": [{"name": "bad/name"}]}, "stage_name"),
        ({"stages": [{"name": "prod-a"}, {"name": "prod_a"}]}, "stage_name"),
        ({"stages": [{"name": "prod", "auto_deploy": "yes"}]}, "stage_name"),
        ({"stages": [{"name": "prod", "access_logging_enabled": True}]}, "stage_name"),
        (
            {
                "stages": [
                    {"name": "prod", "access_log_destination_arn": "arn:external"}
                ]
            },
            "stage_name",
        ),
        ({"access_log_destination_arn": "arn:external"}, "stage_name"),
        ({"access_log_format": "$context.requestId"}, "log_format"),
        (
            {"stages": [{"name": "prod", "access_log_format": "$context.requestId"}]},
            "log_format",
        ),
    ],
)
def test_manual_ownership_and_invalid_stages_are_rejected_in_generation_and_preview(
    changes, field
):
    payload = architecture()
    payload["resources"][0]["config"].update(changes)
    for operation in (
        generate,
        lambda value: ConnectionPreviewer().preview_all(project(value)),
    ):
        with pytest.raises(InvalidConnectionConfigError, match=field):
            operation(payload)


@pytest.mark.parametrize("different_target", [True, False])
def test_conflicting_stage_bindings_are_rejected(different_target):
    payload = architecture()
    if different_target:
        group = deepcopy(payload["resources"][1])
        group.update(name="other-logs", id="other-logs")
        payload["resources"].append(group)
        append_binding(payload, "$default", "other-logs")
    else:
        append_binding(payload, "$default", log_format="$context.requestId")
    for operation in (
        generate,
        lambda value: ConnectionPreviewer().preview_all(project(value)),
    ):
        with pytest.raises(InvalidConnectionConfigError, match="only one"):
            operation(payload)


def test_unknown_stage_is_rejected():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"stage_name": "absent"}
    with pytest.raises(InvalidConnectionConfigError, match="Select a stage"):
        generate(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("stage_name", "bad/stage"),
        ("log_format", ""),
        ("log_format", "$context.requestIdSuffix"),
        ("log_format", "$context.extendedRequestId"),
        ("log_format", "$context.requestId\nsecond line"),
        ("log_format", "$context.requestId\rsecond line"),
    ],
)
def test_typed_settings_reject_invalid_selectors_and_formats(field, value):
    with pytest.raises(ValidationError):
        ApiGatewayLogsConfig.model_validate({field: value})


def test_region_checks_respect_environment_overrides():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    for operation in (
        generate,
        lambda value: ConnectionPreviewer().preview_all(project(value)),
    ):
        with pytest.raises(CrossRegionConnectionError):
            operation(payload)
    payload["environments"][0]["variables"] = {"region": "eu-west-1"}
    assert resources(generate(payload), "aws_apigatewayv2_stage")


def test_preview_describes_delivery_permissions_and_external_encryption():
    payload = architecture()
    payload["resources"][1]["config"]["kms_key_id"] = (
        "arn:aws:kms:us-east-1:123456789012:key/external"
    )
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    text = " ".join(issue.message for issue in preview.issues)
    assert "deployment identity" in text
    assert "external KMS key owner" in text
    assert not preview.iam


def test_unconnected_api_remains_unchanged():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    assert not resources(tree, "aws_apigatewayv2_stage")
    assert not any(path.endswith("/access_logs.tf") for path in tree)


def test_logs_compose_with_lambda_cognito_certificate_grafana_and_managed_encryption():
    payload = mixed_architecture(encrypted=True)
    tree = generate(payload)
    assert len(resources(tree, "aws_apigatewayv2_stage")) == 1
    assert len(resources(tree, "aws_apigatewayv2_api_mapping")) == 1
    assert len(resources(tree, "aws_apigatewayv2_integration")) == 1
    assert resources(tree, "aws_apigatewayv2_route")[0]["authorization_type"] == "JWT"
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    assert len(resources(tree, "aws_kms_key")) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


def native_values():
    return {
        "var.api_access_logs": {
            "$default": {
                "arn": "arn:aws:logs:us-east-1:123456789012:log-group:/access/logs:*",
                "format": DEFAULT_ACCESS_LOG_FORMAT,
            }
        },
        "var.protocol_type": "HTTP",
        "data.aws_partition.api_access_logs.partition": "aws",
        "data.aws_region.api_access_logs.region": "us-east-1",
        "data.aws_caller_identity.api_access_logs.account_id": "123456789012",
    }


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("arn", None, [True, True, True]),
        (
            "arn",
            "arn:aws:logs:us-east-1:123456789012:log-group:/access/logs",
            [True, True, True],
        ),
        (
            "arn",
            "arn:aws:logs:eu-west-1:123456789012:log-group:/access",
            [True, False, True],
        ),
        (
            "arn",
            "arn:aws-cn:logs:us-east-1:123456789012:log-group:/access",
            [True, False, True],
        ),
        (
            "arn",
            "arn:aws:logs:us-east-1:999999999999:log-group:/access",
            [True, False, True],
        ),
        ("arn", "not-a-log-group", [False, False, True]),
        ("format", "$context.requestIdSuffix", [True, True, False]),
        ("format", "$context.requestId\nextra", [True, True, False]),
        ("format", "$context.requestId\r", [True, True, False]),
        ("protocol", "WEBSOCKET", [True, True, False]),
    ],
)
def test_native_destination_and_format_guards(tmp_path, field, value, expected):
    values = native_values()
    if field == "protocol":
        values["var.protocol_type"] = value
    elif value is not None:
        values["var.api_access_logs"]["$default"][field] = value
    expression = (
        "["
        + ", ".join(
            guard["condition"]
            for guard in access_log_preconditions("$default", HCLRenderer())
        )
        + "]"
    )
    assert evaluate(tmp_path, expression, values) == expected


@needs_terraform
@pytest.mark.terraform
def test_literal_format_preserves_terraform_template_markers(tmp_path):
    payload = architecture()
    log_format = '$context.requestId ${literal} %{if quoted} "value"'
    payload["connections"][0]["connection_config"] = {"log_format": log_format}
    contribution = ConnectionProcessor().process_all(project(payload))
    assert (
        evaluate(
            tmp_path,
            contribution.inputs[0].value,
            {
                "module.target-resource.log_group_arn": "arn:aws:logs:us-east-1:123456789012:log-group:/access"
            },
        )["$default"]["format"]
        == log_format
    )


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode",
    ["default", "stages", "shared", "mixed", "encrypted", "external_key", "regional"],
)
def test_generated_projects_validate_and_have_acyclic_graphs(tmp_path, mode):
    payload = (
        mixed_architecture(encrypted=mode == "encrypted")
        if mode in {"mixed", "encrypted"}
        else architecture()
    )
    if mode == "stages":
        payload["resources"][0]["config"]["stages"] = [
            {"name": "qa", "auto_deploy": True},
            {"name": "prod", "auto_deploy": True},
        ]
        append_binding(payload, "prod")
    if mode == "regional":
        for resource in payload["resources"]:
            resource["provider_region"] = "eu-west-1"
    if mode == "shared":
        api = deepcopy(payload["resources"][0])
        api.update(name="second-api", id="second-api")
        payload["resources"].append(api)
        payload["connections"].append(
            dict(payload["connections"][0], source="second-api", source_id="second-api")
        )
    if mode == "external_key":
        payload["resources"][1]["config"]["kms_key_id"] = (
            "arn:aws:kms:us-east-1:123456789012:key/external"
        )
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
