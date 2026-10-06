"""Managed API domains, issuance readiness, coverage guards, and stage mappings."""

import json
import re
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.api_gateway.certificate_domain import domain_preconditions
from app.generators.hcl_renderer import HCLRenderer
from app.models.api_gateway_domains import ApiGatewayDomainBinding
from app.models.connection_configs.api_gateway_certificate import (
    ApiGatewayCertificateConfig,
)
from app.models.input_models import ServiceType
from app.services.connection_handlers.api_gateway_certificate_bindings import (
    certificate_covers_domain,
)
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from tests.conftest import dns_label_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import bind_lambda, file_with, resources
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate, project


def architecture(protocol="HTTP", private=False):
    payload = connection_architecture(
        resolve_spec(ServiceType.CERTIFICATE_MANAGER, ServiceType.API_GATEWAY, None, {})
    )
    payload["resources"][1]["config"]["protocol_type"] = protocol
    if protocol == "WEBSOCKET":
        payload["resources"][1]["config"].update(
            route_selection_expression="$request.body.action", stages=[{"name": "prod"}]
        )
    if private:
        issuer = connection_architecture(
            resolve_spec(
                ServiceType.PRIVATE_CERTIFICATE_AUTHORITY,
                ServiceType.CERTIFICATE_MANAGER,
                None,
                {},
            )
        )
        authority = issuer["resources"][0]
        authority.update(name="issuer", id="issuer")
        payload["resources"].append(authority)
        connection = issuer["connections"][0]
        connection.update(
            source="issuer",
            source_id="issuer",
            target="source-resource",
            target_id="src",
        )
        payload["connections"].append(connection)
    return payload


def append_mapping(payload, **config):
    connection = deepcopy(payload["connections"][0])
    connection["connection_config"].update(config)
    payload["connections"].append(connection)


def compose_cognito_lambda(payload):
    authentication = connection_architecture(
        resolve_spec(ServiceType.COGNITO, ServiceType.API_GATEWAY, None, {})
    )
    payload["resources"][1]["config"]["routes"] = authentication["resources"][1][
        "config"
    ]["routes"]
    pool = authentication["resources"][0]
    pool.update(name="pool", id="pool")
    payload["resources"].append(pool)
    connection = authentication["connections"][0]
    connection.update(source="pool", source_id="pool")
    payload["connections"].append(connection)
    bind_lambda(payload)


def test_domains_compose_with_cognito_authentication_and_lambda_routes():
    payload = architecture()
    compose_cognito_lambda(payload)
    tree = generate(payload)
    route = resources(tree, "aws_apigatewayv2_route")[0]
    assert route["authorization_type"] == "JWT"
    assert len(resources(tree, "aws_apigatewayv2_integration")) == 1
    assert len(resources(tree, "aws_apigatewayv2_stage")) == 1
    assert len(resources(tree, "aws_apigatewayv2_domain_name")) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_http_domain_and_root_mapping_reference_issued_certificate_and_default_stage():
    payload = architecture()
    tree = generate(payload)
    domain = resources(tree, "aws_apigatewayv2_domain_name")[0]
    settings = domain["domain_name_configuration"][0]
    assert domain["domain_name"] == "api.example.com"
    assert settings["certificate_arn"] == "${var.acm_source-resource_certificate_arn}"
    assert settings["endpoint_type"] == "REGIONAL"
    assert settings["security_policy"] == "TLS_1_2"
    assert len(domain["lifecycle"][0]["precondition"]) == 3
    mapping = resources(tree, "aws_apigatewayv2_api_mapping")[0]
    assert mapping["api_id"] == "${aws_apigatewayv2_api.target-resource.id}"
    assert (
        mapping["stage"] == "${aws_apigatewayv2_stage.target-resource_default_stage.id}"
    )
    assert "api_mapping_key" not in mapping
    assert resources(tree, "aws_apigatewayv2_stage")[0]["auto_deploy"] is True
    main = file_with(tree, "/environments/dev/main.tf")
    assert (
        "acm_source-resource_certificate_arn = module.source-resource.issued_certificate_arn"
        in main
    )
    assert (
        "acm_source-resource_certificate_names = module.source-resource.api_gateway_certificate_names"
        in main
    )
    outputs = file_with(tree, "/api-gateway/target-resource/outputs.tf")
    for suffix in ("name", "arn", "target_domain_name", "hosted_zone_id"):
        assert f'_{suffix}"' in outputs
    contribution = ConnectionProcessor().process_all(project(payload))
    assert {(item.module, item.filename) for item in contribution.resources} == {
        ("source-resource", "certificate_issuance.tf"),
        ("target-resource", "certificate_domains.tf"),
    }
    assert not contribution.iam
    assert "module." not in file_with(
        tree, "/api-gateway/target-resource/certificate_domains.tf"
    )


@pytest.mark.parametrize("private", [False, True])
def test_public_and_private_certificate_readiness(private):
    tree = generate(architecture(private=private))
    assert len(resources(tree, "aws_acm_certificate_validation")) == (
        0 if private else 1
    )
    outputs = file_with(tree, "/certificate-manager/source-resource/outputs.tf")
    assert 'output "issued_certificate_arn"' in outputs
    assert "aws_acm_certificate.source-resource.domain_name" in outputs
    assert (
        "tolist(aws_acm_certificate.source-resource.subject_alternative_names)"
        in outputs
    )
    assert "PRIVATE KEY" not in "\n".join(tree.values())


@pytest.mark.parametrize("stage", ["", "prod"])
def test_selects_first_or_named_existing_http_stage(stage):
    payload = architecture()
    payload["resources"][1]["config"]["stages"] = [
        {"name": "qa", "auto_deploy": True},
        {"name": "prod", "auto_deploy": True},
    ]
    payload["connections"][0]["connection_config"].update(
        stage_name=stage, api_mapping_key="orders/v1"
    )
    mapping = resources(generate(payload), "aws_apigatewayv2_api_mapping")[0]
    assert (
        mapping["stage"]
        == f"${{aws_apigatewayv2_stage.target-resource_{stage or 'qa'}_stage.id}}"
    )
    assert mapping["api_mapping_key"] == "orders/v1"


@given(
    labels=st.lists(dns_label_st, min_size=1, max_size=4, unique=True),
    duplicates=st.integers(min_value=1, max_value=3),
)
@settings(max_examples=15, deadline=None)
def test_domains_and_mappings_aggregate_without_resource_or_path_collisions(
    labels, duplicates
):
    payload = architecture()
    payload["resources"][0]["config"].update(
        domain_name="*.example.com", subject_alternative_names=["example.com"]
    )
    connection = payload["connections"].pop()
    for label in labels:
        for path in ("", "v1", "v1/orders", "v1-orders", "v1_orders"):
            item = deepcopy(connection)
            item["connection_config"].update(
                domain_name=f"{label}.example.com", api_mapping_key=path
            )
            payload["connections"].extend(deepcopy(item) for _ in range(duplicates))
    tree = generate(payload)
    assert len(resources(tree, "aws_apigatewayv2_domain_name")) == len(labels)
    assert len(resources(tree, "aws_apigatewayv2_api_mapping")) == len(labels) * 5
    assert len(resources(tree, "aws_acm_certificate_validation")) == 1
    contribution = ConnectionProcessor().process_all(project(payload))
    assert len(contribution.inputs) == 2
    assert len(contribution.outputs) == 2 + len(labels) * 4
    assert len(contribution.resources) == 2
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_multiple_certificates_with_similar_names_have_distinct_inputs():
    payload = architecture()
    other = deepcopy(payload["resources"][0])
    other.update(name="source_resource", id="other")
    other["config"]["domain_name"] = "other.example.com"
    payload["resources"].append(other)
    connection = deepcopy(payload["connections"][0])
    connection.update(
        source="source_resource",
        source_id="other",
        connection_config={"domain_name": "other.example.com"},
    )
    payload["connections"].append(connection)
    tree = generate(payload)
    assert len(resources(tree, "aws_apigatewayv2_domain_name")) == 2
    inputs = ConnectionProcessor().process_all(project(payload)).inputs
    assert len(inputs) == len({item.name for item in inputs}) == 4
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_same_domain_with_different_paths_can_select_different_stages():
    payload = architecture()
    payload["resources"][1]["config"]["stages"] = [{"name": "qa"}, {"name": "prod"}]
    append_mapping(payload, stage_name="prod", api_mapping_key="production")
    tree = generate(payload)
    assert len(resources(tree, "aws_apigatewayv2_domain_name")) == 1
    assert len(resources(tree, "aws_apigatewayv2_api_mapping")) == 2


def test_conflicting_mapping_stages_are_rejected():
    payload = architecture()
    payload["resources"][1]["config"]["stages"] = [{"name": "qa"}, {"name": "prod"}]
    append_mapping(payload, stage_name="prod")
    with pytest.raises(InvalidConnectionConfigError, match="only one stage"):
        generate(payload)


def test_same_domain_cannot_have_competing_certificates():
    payload = architecture()
    other = deepcopy(payload["resources"][0])
    other.update(name="other", id="other")
    payload["resources"].append(other)
    append_mapping(payload)
    payload["connections"][-1].update(source="other", source_id="other")
    for reverse in (False, True):
        if reverse:
            payload["connections"].reverse()
        with pytest.raises(InvalidConnectionConfigError, match="one certificate"):
            generate(payload)


@pytest.mark.parametrize("protocol", ["HTTP", "WEBSOCKET"])
def test_same_regional_hostname_cannot_have_multiple_api_module_owners(protocol):
    payload = architecture()
    other = deepcopy(payload["resources"][1])
    other.update(name="another-api", id="other")
    other["config"].update(
        protocol_type=protocol,
        stages=[{"name": "prod"}],
        route_selection_expression="$request.body.action",
    )
    payload["resources"].append(other)
    append_mapping(payload)
    payload["connections"][-1].update(target="another-api", target_id="other")
    with pytest.raises(InvalidConnectionConfigError, match="one API module owner"):
        generate(payload)


def test_manual_domain_is_preserved_and_managed_hostname_collision_rejected():
    payload = architecture()
    payload["resources"][1]["config"]["custom_domain"] = {
        "domain_name": "external.example.com",
        "certificate_arn": "arn:aws:acm:us-east-1:123456789012:certificate/external",
    }
    tree = generate(payload)
    domains = resources(tree, "aws_apigatewayv2_domain_name")
    assert {item["domain_name"] for item in domains} == {
        "external.example.com",
        "api.example.com",
    }
    payload["resources"][1]["config"]["custom_domain"]["domain_name"] = (
        "api.example.com"
    )
    with pytest.raises(InvalidConnectionConfigError, match="manually configured"):
        generate(payload)


@pytest.mark.parametrize(
    "hostname,names,covered",
    [
        ("api.example.com", ["api.example.com"], True),
        ("api.example.com", ["example.com", "*.example.com"], True),
        ("example.com", ["*.example.com"], False),
        ("nested.api.example.com", ["*.example.com"], False),
        ("api.badexample.com", ["*.example.com"], False),
        ("*.example.com", ["*.example.com"], True),
        ("*.example.com", ["api.example.com"], False),
    ],
)
def test_certificate_primary_and_san_wildcard_coverage(hostname, names, covered):
    assert certificate_covers_domain(hostname, names) is covered
    payload = architecture()
    payload["resources"][0]["config"].update(
        domain_name=names[0], subject_alternative_names=names[1:]
    )
    payload["connections"][0]["connection_config"]["domain_name"] = hostname
    if covered:
        assert (
            resources(generate(payload), "aws_apigatewayv2_domain_name")[0][
                "domain_name"
            ]
            == hostname
        )
    else:
        with pytest.raises(InvalidConnectionConfigError, match="must cover"):
            generate(payload)


@pytest.mark.parametrize(
    "config,field",
    [
        ({"security_policy": "TLS_1_0"}, "domain_name"),
        ({"endpoint_type": "EDGE"}, "domain_name"),
        ({"protocol_type": "REST"}, "domain_name"),
        ({"stages": [{"name": "prod-v1"}, {"name": "prod_v1"}]}, "stage_name"),
        ({"stages": [{"name": "invalid/name"}]}, "stage_name"),
        ({"stages": [{"name": None}]}, "stage_name"),
        ({"stages": [{"name": 1}]}, "stage_name"),
        ({"stages": [{"name": "prod", "auto_deploy": "false"}]}, "stage_name"),
    ],
)
def test_unsupported_domain_and_stage_configuration(config, field):
    payload = architecture()
    payload["resources"][1]["config"].update(config)
    with pytest.raises(InvalidConnectionConfigError) as error:
        generate(payload)
    assert field in str(error.value)
    with pytest.raises(InvalidConnectionConfigError):
        ConnectionPreviewer().preview_all(project(payload))


def test_unknown_stage_is_rejected():
    payload = architecture()
    payload["connections"][0]["connection_config"]["stage_name"] = "missing"
    with pytest.raises(InvalidConnectionConfigError, match="Select a stage"):
        generate(payload)


def test_websocket_stage_reference_and_deployment_preview():
    payload = architecture("WEBSOCKET")
    mapping = resources(generate(payload), "aws_apigatewayv2_api_mapping")[0]
    assert mapping["stage"] == "${aws_apigatewayv2_stage.target-resource_prod_stage.id}"
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert any("Deploy API changes" in issue.message for issue in preview.issues)
    assert not resources(generate(payload), "aws_apigatewayv2_deployment")


@pytest.mark.parametrize(
    "stages",
    [None, [], [{"name": "$default"}], [{"name": "prod", "auto_deploy": True}]],
)
def test_websocket_requires_supported_explicit_stage(stages):
    payload = architecture("WEBSOCKET")
    payload["resources"][1]["config"]["stages"] = stages
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_websocket_mapping_path_is_single_segment():
    payload = architecture("WEBSOCKET")
    payload["connections"][0]["connection_config"]["api_mapping_key"] = "v1/orders"
    with pytest.raises(InvalidConnectionConfigError, match="single path segment"):
        generate(payload)


def test_http_mutual_tls_preserves_external_truststore_and_reports_default_endpoint():
    payload = architecture()
    payload["resources"][1]["config"].update(
        mutual_tls_truststore_uri="s3://truststore/ca.pem",
        mutual_tls_truststore_version="version-1",
    )
    domain = resources(generate(payload), "aws_apigatewayv2_domain_name")[0]
    assert (
        domain["mutual_tls_authentication"][0]["truststore_uri"]
        == "s3://truststore/ca.pem"
    )
    assert domain["mutual_tls_authentication"][0]["truststore_version"] == "version-1"
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert any("Disable the default" in issue.message for issue in preview.issues)
    payload["resources"][1]["config"]["disable_execute_api_endpoint"] = True
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert not any("Disable the default" in issue.message for issue in preview.issues)


@pytest.mark.parametrize(
    "protocol,private,config",
    [
        ("HTTP", True, {"mutual_tls_truststore_uri": "s3://trust/ca.pem"}),
        ("WEBSOCKET", False, {"mutual_tls_truststore_uri": "s3://trust/ca.pem"}),
        ("HTTP", False, {"mutual_tls_truststore_uri": "https://trust/ca.pem"}),
        ("HTTP", False, {"mutual_tls_truststore_version": "version"}),
        (
            "HTTP",
            False,
            {"mutual_tls_authentication": {"truststore_uri": "s3://trust/ca.pem"}},
        ),
    ],
)
def test_unsupported_mutual_tls_settings_are_rejected(protocol, private, config):
    payload = architecture(protocol, private)
    payload["resources"][1]["config"].update(config)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_private_wildcard_domain_is_rejected():
    payload = architecture(private=True)
    payload["resources"][0]["config"]["domain_name"] = "*.example.com"
    payload["connections"][0]["connection_config"]["domain_name"] = "*.example.com"
    with pytest.raises(InvalidConnectionConfigError, match="concrete TLS domains"):
        generate(payload)


@pytest.mark.parametrize("target_region", [None, "us-east-1"])
def test_effective_certificate_and_domain_regions_must_match(target_region):
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    payload["resources"][1]["provider_region"] = target_region
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)


def test_environment_region_override_moves_certificate_and_api_together():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    payload["environments"][0]["variables"] = {"region": "us-west-2"}
    assert 'region = "us-west-2"' in file_with(
        generate(payload), "/environments/dev/provider.tf"
    )


def test_preview_describes_domain_mapping_and_validation_prerequisites():
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    assert [(item.module, item.resource_type) for item in preview.resources] == [
        ("source-resource", "aws_acm_certificate_validation"),
        ("target-resource", "aws_apigatewayv2_domain_name"),
        ("target-resource", "aws_apigatewayv2_api_mapping"),
    ]
    assert not preview.iam
    assert any("Configure DNS" in issue.message for issue in preview.issues)
    assert any("DNS or email" in issue.message for issue in preview.issues)


def test_shared_certificate_with_vpn_has_one_issuance_waiter():
    payload = architecture()
    vpn = connection_architecture(
        resolve_spec(ServiceType.CERTIFICATE_MANAGER, ServiceType.CLIENT_VPN, None, {})
    )
    target = vpn["resources"][1]
    target.update(name="vpn", id="vpn")
    payload["resources"].append(target)
    connection = vpn["connections"][0]
    connection.update(target="vpn", target_id="vpn")
    payload["connections"].append(connection)
    tree = generate(payload)
    assert len(resources(tree, "aws_acm_certificate_validation")) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "hostname",
    [
        "https://api.example.com",
        "api.example.com/path",
        "api.example.com:443",
        "127.0.0.1",
        "api..example.com",
        "api_example.com",
        "-api.example.com",
        "a" * 64 + ".example.com",
        "foo.*.example.com",
    ],
)
def test_invalid_domain_names(hostname):
    with pytest.raises(ValidationError):
        ApiGatewayCertificateConfig(domain_name=hostname)


@pytest.mark.parametrize(
    "path",
    ["/v1", "v1/", "v1//orders", "a" * 301, "v1?q=1", "v1#fragment", "v1 orders"],
)
def test_invalid_mapping_paths(path):
    with pytest.raises(ValidationError):
        ApiGatewayCertificateConfig(domain_name="api.example.com", api_mapping_key=path)


def test_config_normalization_unknown_fields_and_reverse_pair():
    request = ApiGatewayCertificateConfig(domain_name="  API.Example.Com  ")
    assert request.domain_name == "api.example.com"
    assert request.stage_name == request.api_mapping_key == ""
    with pytest.raises(ValidationError):
        ApiGatewayCertificateConfig(
            domain_name="api.example.com", certificate_arn="external"
        )
    assert (
        resolve_spec(ServiceType.API_GATEWAY, ServiceType.CERTIFICATE_MANAGER, None, {})
        is None
    )


@needs_terraform
@pytest.mark.parametrize(
    "region,account,names,expected",
    [
        ("us-east-1", "123456789012", ["api.example.com"], [True, True, True]),
        ("us-east-1", "123456789012", ["*.example.com"], [True, True, True]),
        ("eu-west-1", "123456789012", ["api.example.com"], [False, True, True]),
        ("us-east-1", "999999999999", ["api.example.com"], [True, False, True]),
        ("us-east-1", "123456789012", ["*.com"], [True, True, False]),
        ("us-east-1", "123456789012", [], [True, True, False]),
    ],
)
def test_native_domain_guards_evaluate_certificate_overrides(
    tmp_path, region, account, names, expected
):
    binding = ApiGatewayDomainBinding("api", "cert", "api.example.com", "$default", "")
    expressions = [
        str(item["condition"]) for item in domain_preconditions(binding, HCLRenderer())
    ]
    replacements = {
        f"var.{binding.certificate_input}": json.dumps(
            f"arn:aws:acm:{region}:{account}:certificate/example"
        ),
        f"var.{binding.certificate_names_input}": json.dumps(names),
        "data.aws_region.api_custom_domains.name": '"us-east-1"',
        "data.aws_caller_identity.api_custom_domains.account_id": '"123456789012"',
    }
    for key, value in replacements.items():
        expressions = [expression.replace(key, value) for expression in expressions]
    result = subprocess.run(
        ["terraform", "console"],
        input="[" + ", ".join(expressions) + "]",
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert re.findall(r"\b(true|false)\b", result.stdout) == [
        str(value).lower() for value in expected
    ]


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "protocol,private",
    [("HTTP", False), ("HTTP", True), ("WEBSOCKET", False), ("WEBSOCKET", True)],
)
def test_certificate_domain_projects_validate_and_have_no_cycles(
    tmp_path, protocol, private
):
    payload = architecture(protocol, private)
    if protocol == "HTTP":
        append_mapping(payload, api_mapping_key="v1/orders")
        compose_cognito_lambda(payload)
    tree = generate(payload)
    _write_tree(tmp_path, tree)
    environment = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], environment.parent
    )
    _run_terraform(["validate"], environment.parent)
    _run_terraform(["graph", "-type=plan"], environment.parent)
