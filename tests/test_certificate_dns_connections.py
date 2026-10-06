"""Hosted-zone coverage, shared CNAME ownership, and certificate readiness."""

import json
import re
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.generators.certificate_dns import (
    certificate_dns_preconditions,
    zone_dns_preconditions,
)
from app.generators.hcl_renderer import HCLRenderer
from app.models.connection_configs.certificate_dns import CertificateDnsConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.certificate_dns_bindings import (
    resolve_certificate_dns,
)
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from tests.conftest import dns_label_st
from tests.generator_helpers import connection_architecture
from tests.test_api_gateway_certificate_connections import (
    architecture as api_architecture,
)
from tests.test_client_vpn_certificate_connections import (
    architecture as vpn_architecture,
)
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
        resolve_spec(ServiceType.ROUTE53, ServiceType.CERTIFICATE_MANAGER, None, {})
    )


def connect_zone(payload, certificate, zone="zone", domain="example.com", ttl=60):
    template = architecture()
    if not any(item["name"] == zone for item in payload["resources"]):
        resource = template["resources"][0]
        resource.update(name=zone, id=zone)
        resource["config"]["zone_name"] = domain
        payload["resources"].append(resource)
    target = next(item for item in payload["resources"] if item["name"] == certificate)
    connection = template["connections"][0]
    connection.update(
        source=zone,
        source_id=zone,
        target=certificate,
        target_id=target["id"],
        connection_config={"ttl": ttl},
    )
    payload["connections"].append(connection)


def test_validation_records_are_zone_owned_and_consumers_receive_ready_arns():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"ttl": 300}
    tree = generate(payload)
    record = resources(tree, "aws_route53_record")[0]
    assert record["zone_id"] == "${aws_route53_zone.source-resource.zone_id}"
    assert record["ttl"] == "${each.value.ttl}"
    assert "allow_overwrite" not in record
    assert '"example.com" = {' in file_with(tree, "/source-resource/certificate_dns.tf")
    assert "ttl = 300" in file_with(tree, "/source-resource/certificate_dns.tf")
    waiter = resources(tree, "aws_acm_certificate_validation")[0]
    assert "dns_source-resource_validation_fqdns" in waiter["validation_record_fqdns"]
    outputs = file_with(tree, "/target-resource/outputs.tf")
    assert (
        "aws_acm_certificate_validation.target-resource_issuance.certificate_arn"
        in outputs
    )
    assert "aws_acm_certificate.target-resource.domain_validation_options" in outputs
    assert "aws_acm_certificate.target-resource.arn" not in outputs
    assert "/source-resource/certificate_dns.tf" in " ".join(tree)
    assert "/target-resource/certificate_issuance.tf" in " ".join(tree)


@given(label=dns_label_st, more=st.lists(dns_label_st, max_size=5, unique=True))
@settings(max_examples=30)
def test_wildcard_apex_and_repeated_connectors_share_stable_plan_keys(label, more):
    payload = architecture()
    names = [f"{label}.example.com", *(f"{name}.example.com" for name in more)]
    payload["resources"][1]["config"].update(
        domain_name=names[0],
        subject_alternative_names=[f"*.{name}" for name in names] + names,
    )
    original = generate(payload)
    payload["connections"].append(deepcopy(payload["connections"][0]))
    assert generate(payload) == original
    binding = resolve_certificate_dns(project(payload))[0]
    assert {record.domain for record in binding.records} == set(names)
    text = file_with(original, "/source-resource/certificate_dns.tf")
    for name in set(names):
        assert text.count(f'"{name}" = {{') == 1
    assert "for_each = {" in text


def test_multiple_zones_use_the_most_specific_suffix_and_cover_all_sans():
    payload = architecture()
    payload["resources"][1]["config"]["subject_alternative_names"] = [
        "api.child.example.com",
        "www.example.net",
    ]
    connect_zone(payload, "target-resource", "child", "child.example.com")
    connect_zone(payload, "target-resource", "other", "example.net")
    bindings = resolve_certificate_dns(project(payload))
    assert {item.domain: item.zone_name for item in bindings[0].records} == {
        "example.com": "source-resource",
        "api.child.example.com": "child",
        "www.example.net": "other",
    }
    tree = generate(payload)
    assert len(resources(tree, "aws_route53_record")) == 3
    assert len(resources(tree, "aws_acm_certificate_validation")) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_dns_connection_config_and_direction_are_backend_owned():
    assert CertificateDnsConfig().ttl == 60
    with pytest.raises(ValidationError):
        CertificateDnsConfig(zone_id="external")
    assert (
        resolve_spec(ServiceType.CERTIFICATE_MANAGER, ServiceType.ROUTE53, None, {})
        is None
    )


def test_shared_certificates_across_regions_use_one_record_owner():
    payload = architecture()
    second = deepcopy(payload["resources"][1])
    second.update(name="another", id="another", region="us-west-2")
    second["config"]["subject_alternative_names"] = ["*.example.com"]
    payload["resources"].append(second)
    connect_zone(payload, "another", "source-resource")
    tree = generate(payload)
    assert len(resources(tree, "aws_route53_record")) == 1
    assert len(resources(tree, "aws_acm_certificate_validation")) == 2
    contributions = ConnectionProcessor().process_all(project(payload))
    source_inputs = [
        item for item in contributions.inputs if item.module == "source-resource"
    ]
    assert [item.value for item in source_inputs] == [
        "module.another.domain_validation_options"
    ]
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("email", "DNS"),
        ("private_zone", "public hosted zone"),
        ("uncovered", "uncovered"),
        ("suffix", "uncovered"),
        ("malformed_certificate", "DNS hostname"),
        ("malformed_zone", "DNS hostname"),
        ("double_dot_zone", "DNS hostname"),
        ("wildcard_length", "DNS hostname"),
        ("empty_san", "DNS hostname"),
        ("ttl", "same TTL"),
        ("ambiguous_zone", "Multiple connected"),
        ("shared_zone", "one hosted zone"),
        ("shared_ttl", "one hosted zone"),
        ("private_certificate", "Private CA"),
        ("private_association", "public hosted zone"),
    ],
)
def test_invalid_dns_relationships_fail_before_generation_and_preview(mutation, match):
    payload = architecture()
    if mutation == "email":
        payload["resources"][1]["config"]["validation_method"] = "EMAIL"
    elif mutation == "private_zone":
        payload["resources"][0]["config"]["private_zone"] = True
    elif mutation == "uncovered":
        payload["resources"][1]["config"]["subject_alternative_names"] = ["example.net"]
    elif mutation == "suffix":
        payload["resources"][1]["config"]["domain_name"] = "notexample.com"
    elif mutation == "malformed_certificate":
        payload["resources"][1]["config"]["domain_name"] = "https://example.com"
    elif mutation == "malformed_zone":
        payload["resources"][0]["config"]["zone_name"] = "*.example.com"
    elif mutation == "double_dot_zone":
        payload["resources"][0]["config"]["zone_name"] = "example.com.."
    elif mutation == "wildcard_length":
        payload["resources"][1]["config"]["domain_name"] = "*." + ".".join(
            ["a" * 63] * 3 + ["b" * 61]
        )
    elif mutation == "empty_san":
        payload["resources"][1]["config"]["subject_alternative_names"] = [""]
    elif mutation == "ttl":
        repeated = deepcopy(payload["connections"][0])
        repeated["connection_config"] = {"ttl": 300}
        payload["connections"].append(repeated)
    elif mutation == "ambiguous_zone":
        connect_zone(payload, "target-resource", "duplicate")
    elif mutation in {"shared_zone", "shared_ttl"}:
        second = deepcopy(payload["resources"][1])
        second.update(name="another", id="another")
        payload["resources"].append(second)
        connect_zone(
            payload,
            "another",
            "duplicate" if mutation == "shared_zone" else "source-resource",
            ttl=300 if mutation == "shared_ttl" else 60,
        )
    elif mutation == "private_certificate":
        payload = api_architecture(private=True)
        connect_zone(payload, "source-resource")
    elif mutation == "private_association":
        private = connection_architecture(
            resolve_spec(ServiceType.VPC, ServiceType.ROUTE53, None, {})
        )
        vpc = private["resources"][0]
        vpc.update(name="vpc", id="vpc")
        payload["resources"].append(vpc)
        connection = private["connections"][0]
        connection.update(
            source="vpc", source_id="vpc", target="source-resource", target_id="src"
        )
        payload["connections"].append(connection)
    with pytest.raises(InvalidConnectionConfigError, match=match):
        generate(payload)
    with pytest.raises(InvalidConnectionConfigError, match=match):
        ConnectionPreviewer().preview_all(project(payload))


@pytest.mark.parametrize("ttl", [0, -1, 2147483648, "bad"])
def test_invalid_ttls_are_rejected(ttl):
    with pytest.raises(ValidationError):
        CertificateDnsConfig(ttl=ttl)


@pytest.mark.parametrize("consumer", ["api", "vpn"])
def test_dns_and_certificate_consumers_share_one_waiter_in_either_order(consumer):
    payload = api_architecture() if consumer == "api" else vpn_architecture()
    connect_zone(payload, "source-resource")
    tree = generate(payload)
    contribution = ConnectionProcessor().process_all(project(payload))
    assert (
        len(
            [
                item
                for item in contribution.resources
                if item.filename == "certificate_issuance.tf"
            ]
        )
        == 1
    )
    assert len(resources(tree, "aws_acm_certificate_validation")) == 1
    issues = [
        issue
        for preview in ConnectionPreviewer().preview_all(project(payload))
        for issue in preview.issues
    ]
    assert any("Delegate" in issue.message for issue in issues)
    assert not any("DNS or email" in issue.message for issue in issues)
    payload["connections"].reverse()
    assert generate(payload) == tree


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "consumer", ["api", "vpn", "cloudfront", "load_balancer", "shared"]
)
def test_dns_validation_projects_validate_and_have_no_cycles(tmp_path, consumer):
    if consumer in {"api", "vpn"}:
        payload = api_architecture() if consumer == "api" else vpn_architecture()
        connect_zone(payload, "source-resource")
    elif consumer == "shared":
        payload = architecture()
        second = deepcopy(payload["resources"][1])
        second.update(name="another", id="another", region="us-west-2")
        payload["resources"].append(second)
        connect_zone(payload, "another", "source-resource")
    else:
        service = (
            ServiceType.CLOUDFRONT
            if consumer == "cloudfront"
            else ServiceType.LOAD_BALANCER
        )
        payload = connection_architecture(
            resolve_spec(ServiceType.CERTIFICATE_MANAGER, service, None, {})
        )
        payload["resources"][0]["config"].update(
            domain_name="example.com",
            subject_alternative_names=["*.example.com", "www.example.com"],
        )
        connect_zone(payload, "source-resource")
        alias = connection_architecture(
            resolve_spec(ServiceType.ROUTE53, service, None, {})
        )["connections"][0]
        alias.update(source="zone", source_id="zone")
        payload["connections"].append(alias)
        if consumer == "load_balancer":
            listener = connection_architecture(
                resolve_spec(
                    ServiceType.LOAD_BALANCER, ServiceType.TARGET_GROUP, None, {}
                )
            )
            group = listener["resources"][1]
            group.update(name="group", id="group")
            payload["resources"].append(group)
            connection = listener["connections"][0]
            connection.update(
                source="target-resource",
                source_id="tgt",
                target="group",
                target_id="group",
                connection_config={"port": 443, "protocol": "HTTPS"},
            )
            payload["connections"].append(connection)
    tree = generate(payload)
    if consumer == "load_balancer":
        assert (
            resources(tree, "aws_lb_listener")[0]["certificate_arn"]
            == "${var.source_resource_certificate_arn}"
        )
    _write_tree(tmp_path, tree)
    env = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env.parent)
    _run_terraform(["validate"], env.parent)
    _run_terraform(["graph", "-type=plan"], env.parent)


@needs_terraform
@pytest.mark.terraform
def test_new_project_plans_with_unknown_dns_tokens_and_duplicate_wildcards(tmp_path):
    payload = architecture()
    payload["resources"][1]["config"].update(
        subject_alternative_names=["*.example.com", "www.example.com"]
    )
    tree = generate(payload)
    _write_tree(tmp_path, tree)
    env = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    (env.parent / "dns.tftest.hcl").write_text(
        'mock_provider "aws" {}\nrun "dns_plan" {\n  command = plan\n}\n'
    )
    _run_terraform(_init_args(), env.parent)
    _run_terraform(["test", "-no-color", "-var=aws_region=us-east-1"], env.parent)


@needs_terraform
@pytest.mark.parametrize(
    "method,names,zone,vpc,expected",
    [
        (
            "DNS",
            ["example.com", "*.example.com"],
            "example.com.",
            [],
            [True, True, True, True],
        ),
        ("EMAIL", ["example.com"], "example.com", [], [False, True, True, True]),
        ("DNS", ["example.net"], "example.com", [], [True, False, True, True]),
        (
            "DNS",
            ["example.com", "www.example.com"],
            "example.com",
            [],
            [True, False, True, True],
        ),
        ("DNS", ["EXAMPLE.COM"], "EXAMPLE.COM.", [], [True, True, True, True]),
        ("DNS", ["example.com"], "example.net", [], [True, True, True, False]),
        (
            "DNS",
            ["example.com"],
            "example.com",
            [{"vpc_id": "vpc-12345"}],
            [True, True, False, True],
        ),
    ],
)
def test_native_guards_check_certificate_and_hosted_zone_overrides(
    tmp_path, method, names, zone, vpc, expected
):
    guards = certificate_dns_preconditions(
        ["example.com"], HCLRenderer()
    ) + zone_dns_preconditions("zone", "example.com")
    expressions = [str(item["condition"]) for item in guards]
    replacements = {
        "var.validation_method": method,
        "var.domain_name": names[0],
        "var.subject_alternative_names": names[1:],
        "aws_route53_zone.zone.name": zone,
        "aws_route53_zone.zone.vpc": vpc,
    }
    for reference, value in replacements.items():
        expressions = [
            expression.replace(reference, json.dumps(value))
            for expression in expressions
        ]
    result = subprocess.run(
        ["terraform", "console"],
        input=("[" + ", ".join(expressions) + "]").replace("\n", " "),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert re.findall(r"\b(true|false)\b", result.stdout) == [
        str(value).lower() for value in expected
    ]
