"""Client VPN certificate roles, issuance readiness, and private CA composition."""

import json
import re
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.client_vpn_certificate import certificate_preconditions
from app.models.connection_configs.client_vpn_certificate import (
    ClientVpnCertificateConfig,
)
from app.models.input_models import ServiceType
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


def architecture(role="server", private=False):
    payload = connection_architecture(
        resolve_spec(ServiceType.CERTIFICATE_MANAGER, ServiceType.CLIENT_VPN, None, {})
    )
    payload["resources"][0]["config"]["domain_name"] = "vpn.example.com"
    payload["resources"][1]["config"].update(
        server_certificate_arn="arn:aws:acm:us-east-1:123456789012:certificate/external-server",
        root_certificate_chain_arn="arn:aws:acm:us-east-1:123456789012:certificate/external-client",
    )
    payload["connections"][0]["connection_config"] = {"certificate_role": role}
    if private:
        issuer = connection_architecture(
            resolve_spec(
                ServiceType.PRIVATE_CERTIFICATE_AUTHORITY,
                ServiceType.CERTIFICATE_MANAGER,
                None,
                {},
            )
        )
        ca = issuer["resources"][0]
        ca.update(name="issuer", id="issuer")
        payload["resources"].append(ca)
        connection = issuer["connections"][0]
        connection.update(
            source="issuer",
            source_id="issuer",
            target="source-resource",
            target_id="src",
        )
        payload["connections"].append(connection)
    return payload


@pytest.mark.parametrize(
    "role,fields",
    [
        ("server", ["server_certificate_arn"]),
        ("client_trust", ["root_certificate_chain_arn"]),
        ("both", ["root_certificate_chain_arn", "server_certificate_arn"]),
    ],
)
def test_private_certificate_roles_use_native_references_and_guards(role, fields):
    payload = architecture(role, private=True)
    tree = generate(payload)
    main = file_with(tree, "/environments/dev/main.tf")
    endpoint = resources(tree, "aws_ec2_client_vpn_endpoint")[0]
    assert endpoint["server_certificate_arn"] == "${var.server_certificate_arn}"
    assert (
        endpoint["authentication_options"][0]["root_certificate_chain_arn"]
        == "${var.root_certificate_chain_arn}"
    )
    for field in fields:
        assert f"{field} = module.source-resource.client_vpn_certificate_arn" in main
        assert (
            f"{field}_key_algorithm = module.source-resource.client_vpn_certificate_key_algorithm"
            in main
        )
    for field in set(("server_certificate_arn", "root_certificate_chain_arn")) - set(
        fields
    ):
        assert (
            f'{field} = "arn:aws:acm:us-east-1:123456789012:certificate/external-'
            in main
        )
    assert len(endpoint["lifecycle"][0]["precondition"]) == len(fields) * 2
    assert not resources(tree, "aws_acm_certificate_validation")
    outputs = file_with(tree, "/certificate-manager/source-resource/outputs.tf")
    assert "aws_acm_certificate.source-resource.key_algorithm" in outputs
    assert "aws_acm_certificate.source-resource.arn" in outputs
    assert "PRIVATE KEY" not in "\n".join(tree.values())
    assert not ConnectionProcessor().process_all(project(payload)).iam
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.parametrize("method", ["DNS", "EMAIL"])
def test_public_server_waits_for_issuance_and_preserves_external_client_trust(method):
    payload = architecture()
    payload["resources"][0]["config"]["validation_method"] = method
    tree = generate(payload)
    waiter = resources(tree, "aws_acm_certificate_validation")[0]
    assert waiter["certificate_arn"] == "${aws_acm_certificate.source-resource.arn}"
    assert "validation_record_fqdns" not in waiter
    assert (
        "aws_acm_certificate_validation.source-resource_issuance.certificate_arn"
        in file_with(tree, "/certificate-manager/source-resource/outputs.tf")
    )
    assert "aws_acm_certificate_validation" in file_with(
        tree, "/certificate-manager/source-resource/certificate_issuance.tf"
    )
    assert not resources(tree, "aws_route53_record")


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=4, unique=True),
    duplicates=st.integers(min_value=1, max_value=3),
)
@settings(max_examples=15, deadline=None)
def test_shared_public_certificate_waiter_and_endpoint_inputs_deduplicate(
    names, duplicates
):
    payload = architecture()
    target = payload["resources"].pop(1)
    original = payload["connections"].pop()
    for index, name in enumerate(names):
        endpoint = deepcopy(target)
        endpoint.update(name=f"vpn-{name}", id=f"vpn-{index}")
        payload["resources"].append(endpoint)
        connection = deepcopy(original)
        connection.update(target=endpoint["name"], target_id=endpoint["id"])
        payload["connections"].extend(deepcopy(connection) for _ in range(duplicates))
    tree = generate(payload)
    assert len(resources(tree, "aws_acm_certificate_validation")) == 1
    contribution = ConnectionProcessor().process_all(project(payload))
    assert len(contribution.inputs) == len(names) * 2
    assert len(contribution.outputs) == 3
    assert len(contribution.resources) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_separate_certificates_supply_server_and_client_ca_without_conflicting_inputs():
    payload = architecture("client_trust", private=True)
    certificate = deepcopy(payload["resources"][0])
    certificate.update(name="source_resource", id="server")
    payload["resources"].append(certificate)
    connection = deepcopy(payload["connections"][0])
    connection.update(
        source="source_resource",
        source_id="server",
        connection_config={"certificate_role": "server"},
    )
    payload["connections"].append(connection)
    tree = generate(payload)
    main = file_with(tree, "/environments/dev/main.tf")
    assert (
        "server_certificate_arn = module.source_resource.client_vpn_certificate_arn"
        in main
    )
    assert (
        "root_certificate_chain_arn = module.source-resource.client_vpn_certificate_arn"
        in main
    )
    assert len(resources(tree, "aws_acm_certificate_validation")) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.parametrize("role", ["client_trust", "both"])
def test_public_certificate_cannot_select_client_ca_role(role):
    payload = architecture(role)
    with pytest.raises(InvalidConnectionConfigError, match="private certificate"):
        generate(payload)
    with pytest.raises(InvalidConnectionConfigError):
        ConnectionPreviewer().preview_all(project(payload))


@pytest.mark.parametrize("role", ["server", "client_trust", "both"])
def test_competing_certificates_for_same_role_are_rejected(role):
    payload = architecture(role, private=True)
    certificate = deepcopy(payload["resources"][0])
    certificate.update(name="another", id="another")
    payload["resources"].append(certificate)
    for original in list(payload["connections"]):
        connection = deepcopy(original)
        if connection["source"] == "source-resource":
            connection.update(source="another", source_id="another")
        else:
            connection.update(target="another", target_id="another")
        payload["connections"].append(connection)
    for reverse in (False, True):
        if reverse:
            payload["connections"].reverse()
        with pytest.raises(InvalidConnectionConfigError, match="only one"):
            generate(payload)


@pytest.mark.parametrize("role", ["server", "client_trust", "both"])
@pytest.mark.parametrize(
    "key,signature",
    [("EC_prime256v1", "SHA256WITHECDSA"), ("EC_secp384r1", "SHA384WITHECDSA")],
)
def test_ecdsa_certificates_are_rejected_for_all_roles(role, key, signature):
    payload = architecture(role, private=True)
    payload["resources"][2]["config"].update(
        key_algorithm=key, signing_algorithm=signature
    )
    with pytest.raises(InvalidConnectionConfigError, match="RSA 2048"):
        generate(payload)


@pytest.mark.parametrize("ca_key", ["RSA_2048", "RSA_3072", "RSA_4096"])
def test_large_rsa_issuing_keys_still_use_supported_leaf_keys(ca_key):
    payload = architecture("both", private=True)
    payload["resources"][2]["config"]["key_algorithm"] = ca_key
    assert len(resources(generate(payload), "aws_ec2_client_vpn_endpoint")) == 1


@pytest.mark.parametrize("region", [None, "us-east-1"])
def test_effective_certificate_and_vpn_regions_must_match(region):
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    payload["resources"][1]["provider_region"] = region
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)


def test_environment_region_override_is_supported():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    payload["environments"][0]["variables"] = {"region": "us-west-2"}
    assert 'region = "us-west-2"' in file_with(
        generate(payload), "/environments/dev/provider.tf"
    )


def test_preview_explains_waiter_client_provisioning_and_missing_counterpart():
    payload = architecture()
    payload["resources"][1]["config"]["root_certificate_chain_arn"] = ""
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert [(item.module, item.resource_type) for item in preview.resources] == [
        ("source-resource", "aws_acm_certificate_validation")
    ]
    assert not preview.iam
    messages = " ".join(item.message for item in preview.issues)
    assert "client certificates" in messages and "DNS or email" in messages
    assert "root_certificate_chain_arn" in messages


def test_private_combined_preview_has_no_missing_roles_or_public_validation():
    preview = ConnectionPreviewer().preview_all(
        project(architecture("both", private=True))
    )[0]
    assert not preview.resources and not preview.iam
    assert len(preview.issues) == 1


@pytest.mark.parametrize("value", ["client", "", None, 1])
def test_invalid_roles_are_rejected(value):
    with pytest.raises(ValidationError):
        ClientVpnCertificateConfig(certificate_role=value)


def test_unknown_config_and_reverse_direction_are_rejected():
    assert ClientVpnCertificateConfig().certificate_role == "server"
    with pytest.raises(ValidationError):
        ClientVpnCertificateConfig(certificate_arn="external")
    assert (
        resolve_spec(ServiceType.CLIENT_VPN, ServiceType.CERTIFICATE_MANAGER, None, {})
        is None
    )


@needs_terraform
@pytest.mark.parametrize(
    "region,key,expected",
    [
        ("us-east-1", "RSA_2048", [True, True]),
        ("us-east-1", "RSA_1024", [True, True]),
        ("eu-west-1", "RSA_2048", [False, True]),
        ("us-east-1", "RSA_4096", [True, False]),
        ("us-east-1", "EC_prime256v1", [True, False]),
    ],
)
def test_native_guards_enforce_region_and_leaf_keys(tmp_path, region, key, expected):
    conditions = [
        str(guard["condition"])
        for guard in certificate_preconditions(("server_certificate_arn",))
    ]
    expression = (
        "["
        + ", ".join(
            condition.replace(
                "var.server_certificate_arn_key_algorithm", json.dumps(key)
            )
            .replace(
                "var.server_certificate_arn",
                json.dumps(f"arn:aws:acm:{region}:123456789012:certificate/example"),
            )
            .replace("data.aws_region.client_vpn_certificate.name", '"us-east-1"')
            for condition in conditions
        )
        + "]"
    )
    result = subprocess.run(
        ["terraform", "console"],
        input=expression,
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
    "role,private",
    [("server", False), ("server", True), ("client_trust", True), ("both", True)],
)
def test_certificate_projects_validate_and_have_no_dependency_cycle(
    tmp_path, role, private
):
    tree = generate(architecture(role, private))
    _write_tree(tmp_path, tree)
    environment = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], environment.parent
    )
    _run_terraform(["validate"], environment.parent)
    _run_terraform(["graph", "-type=plan"], environment.parent)
