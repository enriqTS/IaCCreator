"""Private CA activation, renewal permissions, and ACM issuance composition."""

import json
import re
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.hcl_renderer import HCLRenderer
from app.generators.private_certificate import private_certificate_attributes
from app.models.connection_configs.private_certificate import PrivateCertificateConfig
from app.models.input_models import ServiceType
from app.models.private_certificate import PrivateCertificateBinding
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(
            ServiceType.PRIVATE_CERTIFICATE_AUTHORITY,
            ServiceType.CERTIFICATE_MANAGER,
            None,
            {},
        )
    )


def test_ca_activation_and_acm_certificate_use_native_references():
    payload = architecture()
    payload["resources"][1]["config"].update(
        domain_name="service.internal.example.com",
        subject_alternative_names=["*.internal.example.com"],
    )
    tree = generate(payload)
    authority = resources(tree, "aws_acmpca_certificate_authority")[0]
    assert authority["type"] == "ROOT"
    config = authority["certificate_authority_configuration"][0]
    assert config["key_algorithm"] == "${var.key_algorithm}"
    assert config["signing_algorithm"] == "${var.signing_algorithm}"
    assert config["subject"][0]["common_name"] == "${var.common_name}"
    assert "key_algorithm" not in authority and "subject" not in authority
    root = resources(tree, "aws_acmpca_certificate")[0]
    assert (
        root["certificate_authority_arn"]
        == "${aws_acmpca_certificate_authority.source-resource.arn}"
    )
    assert (
        root["certificate_signing_request"]
        == "${aws_acmpca_certificate_authority.source-resource.certificate_signing_request}"
    )
    assert root["signing_algorithm"] == "${var.signing_algorithm}"
    assert root["validity"][0]["type"] == "YEARS"
    assert root["validity"][0]["value"] == 10
    assert "RootCACertificate/V1" in root["template_arn"]
    assert (
        'split(":", aws_acmpca_certificate_authority.source-resource.arn)[1]'
        in file_with(tree, "/acm_issuance.tf")
    )
    activation = resources(tree, "aws_acmpca_certificate_authority_certificate")[0]
    assert (
        activation["certificate"]
        == "${aws_acmpca_certificate.source-resource_acm_root.certificate}"
    )
    assert "certificate_chain" not in activation
    permission = resources(tree, "aws_acmpca_permission")[0]
    assert permission["principal"] == "acm.amazonaws.com"
    assert permission["actions"] == [
        "IssueCertificate",
        "GetCertificate",
        "ListPermissions",
    ]
    assert (
        'source_account = split(":", aws_acmpca_certificate_authority.source-resource.arn)[4]'
        in file_with(tree, "/acm_issuance.tf")
    )
    assert permission["depends_on"] == [
        "${aws_acmpca_certificate_authority_certificate.source-resource_acm_activation}"
    ]
    cert = resources(tree, "aws_acm_certificate")[0]
    assert cert["certificate_authority_arn"] == "${var.private_ca_arn}"
    assert "var.private_ca_key_algorithm" in cert["key_algorithm"]
    assert "validation_method" not in cert
    assert cert["lifecycle"][0]["create_before_destroy"] is True
    assert cert["domain_name"] == "${var.domain_name}"
    assert cert["subject_alternative_names"] == "${var.subject_alternative_names}"
    main = tree["connection-check/environments/dev/main.tf"]
    assert "private_ca_arn = module.source-resource.acm_issuer_arn" in main
    assert (
        "private_ca_key_algorithm = module.source-resource.acm_issuer_key_algorithm"
        in main
    )
    outputs = file_with(
        tree, "/private-certificate-authority/source-resource/outputs.tf"
    )
    assert 'output "root_certificate"' in outputs
    assert (
        "depends_on = [aws_acmpca_certificate_authority_certificate.source-resource_acm_activation, aws_acmpca_permission.source-resource_acm_renewal]"
        in outputs
    )
    assert "module.target-resource" not in outputs
    assert "validation_method" not in file_with(
        tree, "/certificate-manager/target-resource/variables.tf"
    )
    assert "domain_validation_options" not in file_with(
        tree, "/certificate-manager/target-resource/outputs.tf"
    )
    assert "PRIVATE KEY" not in "\n".join(tree.values())
    assert not ConnectionProcessor().process_all(project(payload)).iam
    assert generate(payload) == tree


def test_unconnected_resources_keep_public_acm_and_pending_root_ca():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    cert = resources(tree, "aws_acm_certificate")[0]
    assert cert["validation_method"] == "${var.validation_method}"
    assert "certificate_authority_arn" not in cert
    assert "domain_validation_options" in file_with(
        tree, "/certificate-manager/target-resource/outputs.tf"
    )
    assert not resources(tree, "aws_acmpca_certificate")
    assert not resources(tree, "aws_acmpca_certificate_authority_certificate")
    assert not resources(tree, "aws_acmpca_permission")
    assert (
        "certificate_authority_configuration"
        in resources(tree, "aws_acmpca_certificate_authority")[0]
    )


@pytest.mark.parametrize("validation_method", ["DNS", "EMAIL"])
def test_private_issuance_ignores_public_validation_method(validation_method):
    payload = architecture()
    payload["resources"][1]["config"]["validation_method"] = validation_method
    assert (
        "validation_method"
        not in resources(generate(payload), "aws_acm_certificate")[0]
    )


@pytest.mark.parametrize(
    "ca_key,signing,key",
    [
        ("RSA_2048", "SHA256WITHRSA", "AUTO"),
        ("RSA_3072", "SHA384WITHRSA", "RSA_2048"),
        ("RSA_4096", "SHA512WITHRSA", "RSA_2048"),
        ("EC_prime256v1", "SHA256WITHECDSA", "AUTO"),
        ("EC_secp384r1", "SHA384WITHECDSA", "AUTO"),
        ("EC_prime256v1", "SHA256WITHECDSA", "EC_secp384r1"),
        ("EC_secp384r1", "SHA512WITHECDSA", "EC_prime256v1"),
    ],
)
def test_supported_ca_keys_and_leaf_key_selection(ca_key, signing, key):
    payload = architecture()
    payload["resources"][0]["config"].update(
        key_algorithm=ca_key, signing_algorithm=signing
    )
    payload["connections"][0]["connection_config"] = {"key_algorithm": key}
    tree = generate(payload)
    cert = resources(tree, "aws_acm_certificate")[0]
    if key == "AUTO":
        assert "var.private_ca_key_algorithm" in cert["key_algorithm"]
    else:
        assert cert["key_algorithm"] == key
    preconditions = cert["lifecycle"][0]["precondition"]
    assert "data.aws_region.private_certificate.name" in preconditions[0]["condition"]
    assert "var.private_ca_key_algorithm" in preconditions[1]["condition"]
    root = resources(tree, "aws_acmpca_certificate")[0]
    conditions = root["lifecycle"][0]["precondition"]
    assert "GENERAL_PURPOSE" in conditions[0]["condition"]
    assert "var.key_algorithm" in conditions[1]["condition"]
    assert "var.signing_algorithm" in conditions[1]["condition"]


def add_certificate(payload, name, key="AUTO"):
    certificate = deepcopy(payload["resources"][1])
    certificate.update(id=name, name=name)
    certificate["config"]["domain_name"] = f"{name}.internal.example.com"
    payload["resources"].append(certificate)
    connection = deepcopy(payload["connections"][0])
    connection.update(
        target=name, target_id=name, connection_config={"key_algorithm": key}
    )
    payload["connections"].append(connection)


@settings(max_examples=12)
@given(
    authority_name=resource_name_st,
    count=st.integers(min_value=1, max_value=4),
    copies=st.integers(min_value=1, max_value=3),
    reverse=st.booleans(),
)
def test_ca_activation_is_shared_and_connections_are_order_independent(
    authority_name, count, copies, reverse
):
    payload = architecture()
    payload["resources"][0]["name"] = authority_name
    payload["connections"][0]["source"] = authority_name
    for index in range(count):
        add_certificate(payload, f"certificate-{index}", "RSA_2048")
    expected = generate(payload)
    payload["connections"] *= copies
    if reverse:
        payload["connections"].reverse()
    assert generate(payload) == expected
    assert len(resources(expected, "aws_acmpca_certificate")) == 1
    assert len(resources(expected, "aws_acmpca_certificate_authority_certificate")) == 1
    assert len(resources(expected, "aws_acmpca_permission")) == 1
    assert len(resources(expected, "aws_acm_certificate")) == 1 + count
    outputs = file_with(
        expected, f"/private-certificate-authority/{authority_name}/outputs.tf"
    )
    assert outputs.count('output "acm_issuer_arn"') == 1


@pytest.mark.parametrize("conflict", ["authority", "key"])
def test_conflicting_issuers_or_keys_are_rejected_in_any_order(conflict):
    payload = architecture()
    other = deepcopy(payload["connections"][0])
    if conflict == "authority":
        ca = deepcopy(payload["resources"][0])
        ca.update(name="source_resource", id="other")
        payload["resources"].append(ca)
        other.update(source="source_resource", source_id="other")
    else:
        other["connection_config"]["key_algorithm"] = "RSA_2048"
    payload["connections"].append(other)
    for reverse in (False, True):
        if reverse:
            payload["connections"].reverse()
        with pytest.raises(InvalidConnectionConfigError, match="only one issuing CA"):
            generate(payload)
        with pytest.raises(InvalidConnectionConfigError, match="only one issuing CA"):
            ConnectionPreviewer().preview_all(project(payload))


@pytest.mark.parametrize(
    "ca_updates,leaf_settings",
    [
        ({"usage_mode": "SHORT_LIVED_CERTIFICATE"}, {}),
        ({"usage_mode": "unknown"}, {}),
        ({"key_algorithm": "SM2"}, {}),
        ({"key_algorithm": "EC_secp521r1"}, {}),
        ({"key_algorithm": "RSA_1024"}, {}),
        ({"signing_algorithm": "SHA256WITHECDSA"}, {}),
        ({"signing_algorithm": "unknown"}, {}),
        ({"key_algorithm": "EC_prime256v1"}, {}),
        ({}, {"key_algorithm": "EC_prime256v1"}),
        (
            {"key_algorithm": "EC_secp384r1", "signing_algorithm": "SHA384WITHECDSA"},
            {"key_algorithm": "RSA_2048"},
        ),
    ],
)
def test_invalid_issuance_settings_fail_generation_and_preview(
    ca_updates, leaf_settings
):
    payload = architecture()
    payload["resources"][0]["config"].update(ca_updates)
    payload["connections"][0]["connection_config"] = leaf_settings
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)
    with pytest.raises(InvalidConnectionConfigError):
        ConnectionPreviewer().preview_all(project(payload))


@pytest.mark.parametrize("target_region", [None, "us-east-1"])
def test_different_issuer_and_acm_regions_are_rejected(target_region):
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    payload["resources"][1]["provider_region"] = target_region
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)


def test_environment_region_override_keeps_issuance_references():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    payload["environments"][0]["variables"] = {"region": "us-west-2"}
    tree = generate(payload)
    assert (
        'region = "us-west-2"' in tree["connection-check/environments/dev/provider.tf"]
    )
    assert (
        "module.source-resource.acm_issuer_arn"
        in tree["connection-check/environments/dev/main.tf"]
    )


def connect_consumer(payload, service):
    consumer = connection_architecture(
        resolve_spec(ServiceType.CERTIFICATE_MANAGER, service, "secures", {})
    )
    target = consumer["resources"][1]
    target.update(name="consumer", id="consumer")
    payload["resources"].append(target)
    connection = consumer["connections"][0]
    connection.update(
        source="target-resource",
        source_id="tgt",
        target="consumer",
        target_id="consumer",
    )
    payload["connections"].append(connection)


def test_private_certificate_composes_with_https_listener():
    payload = architecture()
    connect_consumer(payload, ServiceType.LOAD_BALANCER)
    payload["resources"].append(
        {
            "id": "group",
            "name": "app-group",
            "service_type": "target-group",
            "config": {"vpc_id": "vpc-12345678"},
            "terraform_variables": {},
        }
    )
    payload["connections"].append(
        {
            "source": "consumer",
            "source_id": "consumer",
            "target": "app-group",
            "target_id": "group",
            "connection_type": "forwards_to",
            "connection_config": {"port": 443, "protocol": "HTTPS"},
        }
    )
    tree = generate(payload)
    assert (
        resources(tree, "aws_lb_listener")[0]["certificate_arn"]
        == "${var.target_resource_certificate_arn}"
    )
    expected = tree
    payload["connections"].reverse()
    assert generate(payload) == expected


def test_self_signed_ca_cannot_supply_cloudfront_viewer_certificate():
    payload = architecture()
    connect_consumer(payload, ServiceType.CLOUDFRONT)
    for reverse in (False, True):
        if reverse:
            payload["connections"].reverse()
        with pytest.raises(InvalidConnectionConfigError, match="publicly trusted"):
            generate(payload)


def test_preview_describes_root_activation_and_client_trust():
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    assert [item.resource_type for item in preview.resources] == [
        "aws_acmpca_certificate",
        "aws_acmpca_certificate_authority_certificate",
        "aws_acmpca_permission",
    ]
    assert all(item.module == "source-resource" for item in preview.resources)
    assert not preview.iam
    message = preview.issues[0].message
    assert "trust stores" in message and "ten-year" in message and "renewal" in message


@pytest.mark.parametrize("value", ["RSA_4096", "SM2", "rsa_2048", "", None, 2048])
def test_invalid_connection_key_algorithm(value):
    with pytest.raises(ValidationError):
        PrivateCertificateConfig(key_algorithm=value)


def test_unknown_connection_fields_are_rejected():
    with pytest.raises(ValidationError):
        PrivateCertificateConfig(certificate_authority_arn="external")


@needs_terraform
@pytest.mark.parametrize(
    "ca_key,signature,usage,leaf_key,region,expected",
    [
        (
            "RSA_2048",
            "SHA256WITHRSA",
            "GENERAL_PURPOSE",
            "AUTO",
            "us-east-1",
            [True, True, True, True],
        ),
        (
            "EC_secp384r1",
            "SHA384WITHECDSA",
            "GENERAL_PURPOSE",
            "AUTO",
            "us-east-1",
            [True, True, True, True],
        ),
        (
            "RSA_2048",
            "SHA256WITHECDSA",
            "GENERAL_PURPOSE",
            "AUTO",
            "us-east-1",
            [True, False, True, True],
        ),
        (
            "RSA_4096",
            "SHA512WITHRSA",
            "SHORT_LIVED_CERTIFICATE",
            "AUTO",
            "us-east-1",
            [False, True, True, True],
        ),
        (
            "EC_secp384r1",
            "SHA384WITHECDSA",
            "GENERAL_PURPOSE",
            "RSA_2048",
            "us-east-1",
            [True, True, True, False],
        ),
        (
            "RSA_2048",
            "SHA256WITHRSA",
            "GENERAL_PURPOSE",
            "EC_prime256v1",
            "us-east-1",
            [True, True, True, False],
        ),
        (
            "RSA_2048",
            "SHA256WITHRSA",
            "GENERAL_PURPOSE",
            "AUTO",
            "us-west-2",
            [True, True, False, True],
        ),
        (
            "EC_secp521r1",
            "SHA512WITHECDSA",
            "GENERAL_PURPOSE",
            "AUTO",
            "us-east-1",
            [True, False, True, True],
        ),
    ],
)
def test_native_guards_evaluate_key_usage_and_region_overrides(
    tmp_path, ca_key, signature, usage, leaf_key, region, expected
):
    content = file_with(generate(architecture()), "/acm_issuance.tf")
    conditions = [
        item.strip()
        for item in re.findall(
            r"condition = (.*?)\n\s*error_message", content, re.DOTALL
        )
    ]
    attributes = private_certificate_attributes(
        PrivateCertificateBinding("source-resource", leaf_key), HCLRenderer()
    )
    conditions.extend(
        str(item["condition"]) for item in attributes["lifecycle"]["precondition"]
    )
    expression = "jsonencode([" + ", ".join(conditions) + "])"
    for name, value in {
        "var.key_algorithm": ca_key,
        "var.signing_algorithm": signature,
        "var.usage_mode": usage,
        "var.private_ca_key_algorithm": ca_key,
        "var.private_ca_arn": "arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/test",
        "data.aws_region.private_certificate.name": region,
    }.items():
        expression = expression.replace(name, json.dumps(value))
    expression = " ".join(expression.splitlines())
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input=expression + "\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(json.loads(result.stdout)) == expected


@needs_terraform
@pytest.mark.parametrize("ecdsa", [False, True])
def test_private_certificate_project_validates_without_cycles(tmp_path, ecdsa):
    payload = architecture()
    if ecdsa:
        payload["resources"][0]["config"].update(
            key_algorithm="EC_secp384r1", signing_algorithm="SHA384WITHECDSA"
        )
    add_certificate(
        payload, "other-certificate", "EC_prime256v1" if ecdsa else "RSA_2048"
    )
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
