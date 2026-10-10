from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.generators.organization_delegation import (
    CALLER,
    PARTITION,
    READINESS,
    REGION,
    firewall_preconditions,
)
from app.models.connection_configs.organization_delegation import (
    OrganizationDelegationConfig,
)
from app.models.input_models import ServiceType
from app.models.organization_delegation import DELEGATED_SERVICES
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


def architecture(definition=DELEGATED_SERVICES[0]):
    return connection_architecture(
        resolve_spec(ServiceType.ORGANIZATIONS, definition.service, None, {})
    )


def combined():
    payload = architecture()
    for definition in DELEGATED_SERVICES[1:]:
        template = architecture(definition)
        name = definition.service.value
        payload["resources"].append(dict(template["resources"][1], name=name, id=name))
        payload["connections"].append(
            dict(template["connections"][0], target=name, target_id=name)
        )
    return payload


@pytest.mark.parametrize("definition", DELEGATED_SERVICES)
def test_registration_ownership_and_native_context(definition):
    tree = generate(architecture(definition))
    registration = resources(tree, definition.resource)
    assert len(registration) == 1
    assert (
        registration[0][definition.account_argument]
        == "${var.delegated_admin_account_id}"
        if definition.regional
        else registration[0]["account_id"] == "${var.account_id}"
    )
    assert len(registration[0]["lifecycle"][0]["precondition"]) == 4
    organization = resources(tree, "aws_organizations_organization")[0]
    assert definition.principal in organization["aws_service_access_principals"]
    output = file_with(tree, "/source-resource/outputs.tf")
    assert ".non_master_accounts" in output and 'account.state == "ACTIVE"' in output
    assert ".master_account_id" in output
    assert "module.target-resource" not in output
    all_text = "\n".join(tree.values())
    assert "module.source-resource.delegation_context" in all_text
    assert "aws_organizations_delegated_administrator" not in all_text
    assert "aws_iam_role" not in all_text
    contribution = ConnectionProcessor().process_all(project(architecture(definition)))
    assert not contribution.iam
    assert {item.module for item in contribution.resources} == {"target-resource"}
    assert any(
        "management-account" in issue.message
        for issue in ConnectionPreviewer()
        .preview_all(project(architecture(definition)))[0]
        .issues
    )


@given(
    name=resource_name_st,
    duplicates=st.integers(1, 4),
    member=st.integers(1, 999999999999),
)
@settings(max_examples=20, deadline=None)
def test_property_account_identity_duplicate_edges_and_names(name, duplicates, member):
    payload = combined()
    payload["resources"][0]["name"] = "organization-" + name
    for edge in payload["connections"]:
        edge["source"] = payload["resources"][0]["name"]
        edge["connection_config"]["account_id"] = f"{member:012d}"
    payload["resources"][0]["config"]["aws_service_access_principals"] = [
        "cloudtrail.amazonaws.com"
    ]
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * duplicates))
    assert generate(payload) == expected
    trust = resources(expected, "aws_organizations_organization")[0][
        "aws_service_access_principals"
    ]
    assert "var.aws_service_access_principals" in trust
    for definition in DELEGATED_SERVICES:
        assert len(resources(expected, definition.resource)) == 1
        assert definition.principal in trust
    assert "cloudtrail.amazonaws.com" in "\n".join(expected.values())


@pytest.mark.parametrize(
    "value",
    [
        None,
        222222222222,
        True,
        "",
        "123",
        "000000000000",
        "12345678901x",
        " 222222222222",
        "222222222222\n",
        "${member}",
    ],
)
def test_member_id_is_required_and_strict(value):
    with pytest.raises(ValidationError):
        OrganizationDelegationConfig(account_id=value)


def test_missing_member_id_and_unknown_fields():
    with pytest.raises(ValidationError):
        OrganizationDelegationConfig()
    with pytest.raises(ValidationError):
        OrganizationDelegationConfig(account_id="222222222222", assume_role="external")


@pytest.mark.parametrize(
    "case",
    [
        "billing",
        "disabled-detector",
        "paused-macie",
        "inspector-member",
        "inspector-many",
        "inspector-empty-scans",
        "fms-mismatch",
        "fms-region",
        "fms-environment",
        "duplicate-account",
        "duplicate-region",
        "regional-account",
        "collapsed-region",
        "multiple-organizations",
        "unconnected-service",
        "unconnected-organization",
    ],
)
def test_rejects_unsupported_or_conflicting_delegations(case):
    definition = (
        DELEGATED_SERVICES[2]
        if case == "paused-macie"
        else DELEGATED_SERVICES[3]
        if case.startswith("inspector")
        else DELEGATED_SERVICES[4]
        if case.startswith("fms")
        else DELEGATED_SERVICES[0]
    )
    payload = architecture(definition)
    source, target = payload["resources"]
    edge = payload["connections"][0]
    if case == "billing":
        source["config"]["feature_set"] = "CONSOLIDATED_BILLING"
    elif case == "disabled-detector":
        target["config"]["enabled"] = False
    elif case == "paused-macie":
        target["config"]["status"] = "PAUSED"
    elif case == "inspector-member":
        target["config"]["account_ids"] = ["222222222222"]
    elif case == "inspector-many":
        target["config"]["account_ids"] = ["111111111111", "333333333333"]
    elif case == "inspector-empty-scans":
        target["config"]["resource_types"] = []
    elif case == "fms-mismatch":
        target["config"]["account_id"] = "333333333333"
    elif case == "fms-region":
        target["provider_region"] = "eu-west-1"
    elif case == "fms-environment":
        payload["environments"][0]["variables"]["region"] = "eu-west-1"
    elif case == "duplicate-account":
        payload["connections"].append(
            dict(edge, connection_config={"account_id": "333333333333"})
        )
    elif case in {"multiple-organizations", "unconnected-organization"}:
        payload["resources"].append(dict(source, name="other-org", id="other-org"))
        if case == "multiple-organizations":
            payload["connections"].append(
                dict(edge, source="other-org", source_id="other-org")
            )
    else:
        other = deepcopy(target)
        other.update(name="other-target", id="other-target")
        if case in {"regional-account", "collapsed-region"}:
            other["provider_region"] = "eu-west-1"
        payload["resources"].append(other)
        additional_edge = dict(
            edge,
            target="other-target",
            target_id="other-target",
            connection_config={"account_id": "333333333333"}
            if case == "regional-account"
            else edge["connection_config"],
        )
        if case != "unconnected-service":
            payload["connections"].append(additional_edge)
        if case == "collapsed-region":
            payload["environments"][0]["variables"]["region"] = "us-east-1"
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_regional_designations_share_account_and_trust_without_source_region_constraint():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "us-west-2"
    target = dict(
        payload["resources"][1],
        name="other-detector",
        id="other-detector",
        provider_region="eu-west-1",
    )
    payload["resources"].append(target)
    payload["connections"].append(
        dict(payload["connections"][0], target=target["name"], target_id=target["id"])
    )
    tree = generate(payload)
    assert len(resources(tree, "aws_guardduty_organization_admin_account")) == 2
    assert len(resources(tree, "aws_organizations_organization")) == 1


def native_values():
    return {
        "var.organization_context": {
            "id": "o-0123456789ab",
            "arn": "arn:aws:organizations::111111111111:organization/o-0123456789ab",
            "management_account_id": "111111111111",
            "feature_set": "ALL",
            "service_principals": [value.principal for value in DELEGATED_SERVICES],
            "active_member_ids": ["222222222222"],
        },
        "var.delegated_admin_account_id": "222222222222",
        CALLER: "111111111111",
        PARTITION: "aws",
        REGION: "us-east-1",
        "var.account_id": "222222222222",
    }


@needs_terraform
@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "caller",
        "management",
        "member",
        "zero",
        "inactive",
        "trust",
        "feature",
        "arn",
        "partition",
        "region",
        "fms-input",
    ],
)
def test_terraform_membership_identity_and_scope_guards(tmp_path, case):
    values = native_values()
    context = values["var.organization_context"]
    if case == "caller":
        values[CALLER] = "333333333333"
    elif case == "management":
        values["var.delegated_admin_account_id"] = "111111111111"
    elif case == "member":
        values["var.delegated_admin_account_id"] = "333333333333"
    elif case == "zero":
        values["var.delegated_admin_account_id"] = "000000000000"
    elif case == "inactive":
        context["active_member_ids"] = []
    elif case == "trust":
        context["service_principals"] = []
    elif case == "feature":
        context["feature_set"] = "CONSOLIDATED_BILLING"
    elif case == "arn":
        context["arn"] = context["arn"].replace("111111111111", "333333333333")
    elif case == "partition":
        values[PARTITION] = "aws-us-gov"
    elif case == "region":
        values[REGION] = "eu-west-1"
    elif case == "fms-input":
        values["var.account_id"] = "333333333333"
    checks = firewall_preconditions(DELEGATED_SERVICES[-1])
    expression = "alltrue([" + ", ".join(value["condition"] for value in checks) + "])"
    assert evaluate(tmp_path, expression, values) is (case == "valid")


@needs_terraform
@pytest.mark.parametrize("definition", DELEGATED_SERVICES[:4])
@pytest.mark.parametrize("ready", [True, False])
def test_terraform_management_service_readiness(tmp_path, definition, ready):
    values = native_values()
    if definition.service == ServiceType.GUARDDUTY:
        values["aws_guardduty_detector.native"] = {
            "enable": ready,
            "id": "detector",
            "account_id": "111111111111",
            "arn": "arn:aws:guardduty:us-east-1:111111111111:detector/detector",
        }
    elif definition.service == ServiceType.SECURITY_HUB:
        values["aws_securityhub_account.native"] = {
            "arn": f"arn:aws:securityhub:us-east-1:{'111111111111' if ready else '333333333333'}:hub/default"
        }
    elif definition.service == ServiceType.MACIE:
        values["aws_macie2_account.native"] = {
            "status": "ENABLED" if ready else "PAUSED",
            "service_role": "arn:aws:iam::111111111111:role/aws-service-role/macie.amazonaws.com/AWSServiceRoleForAmazonMacie",
        }
    else:
        values["aws_inspector2_enabler.native"] = {
            "account_ids": ["111111111111" if ready else "222222222222"],
            "resource_types": ["EC2"],
        }
    assert (
        evaluate(tmp_path, READINESS[definition.service.value]("native"), values)
        is ready
    )


@pytest.mark.terraform
@needs_terraform
@pytest.mark.parametrize(
    "mode",
    [
        *[definition.service.value for definition in DELEGATED_SERVICES],
        "combined",
        "regional",
        "duplicates",
        "trusted-services",
    ],
)
def test_projects_pass_real_provider_validation_and_acyclic_graphs(tmp_path, mode):
    definition = next(
        (value for value in DELEGATED_SERVICES if value.service.value == mode), None
    )
    payload = architecture(definition) if definition else combined()
    if mode == "regional":
        payload["resources"][0]["provider_region"] = "us-west-2"
        payload["resources"][1]["provider_region"] = "eu-west-1"
        other = dict(
            payload["resources"][1],
            name="other-detector",
            id="other-detector",
            provider_region="us-east-1",
        )
        payload["resources"].append(other)
        payload["connections"].append(
            dict(payload["connections"][0], target=other["name"], target_id=other["id"])
        )
    if mode == "duplicates":
        payload["connections"] = list(reversed(payload["connections"] * 3))
    if mode == "trusted-services":
        payload["resources"][0]["config"]["aws_service_access_principals"] = [
            "cloudtrail.amazonaws.com"
        ]
        payload["resources"][-2]["config"]["account_ids"] = ["111111111111"]
        payload["resources"][-1]["config"]["account_id"] = "222222222222"
    _write_tree(tmp_path, generate(payload))
    root = tmp_path / "connection-check" / "environments" / "dev"
    _run_terraform(
        [argument for argument in _init_args() if argument != "-backend=false"], root
    )
    _run_terraform(["validate"], root)
    _run_terraform(["graph", "-type=plan"], root)
