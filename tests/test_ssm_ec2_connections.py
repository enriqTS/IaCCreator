"""State Manager targets share runtime profiles while retaining per-pair execution settings."""

import json
import re
from copy import deepcopy

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.ssm_ec2 import association_preconditions
from app.models.connection_configs.ssm_ec2 import SsmEc2Config
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_efs_ec2_connections import mixed_architecture as efs_architecture
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
        resolve_spec(ServiceType.SYSTEMS_MANAGER, ServiceType.EC2, None, {})
    )


def document(payload):
    return json.loads(payload["resources"][0]["config"]["content"])


def with_parameters(payload):
    value = document(payload)
    value["parameters"] = {
        "Message": {"type": "String"},
        "Mode": {"type": "String", "default": "check"},
        "Commands": {"type": "StringList", "default": ["echo Ready"]},
    }
    payload["resources"][0]["config"]["content"] = json.dumps(value)
    payload["connections"][0]["connection_config"] = {
        "parameters_json": json.dumps(
            {"Message": "Hello ${operator}, %{literal}\nSecond line"}
        )
    }


def native_values():
    body = document(architecture())
    return {
        "aws_ssm_document.document": {
            "name": "managed-document",
            "arn": "arn:aws:ssm:us-east-1:123456789012:document/managed-document",
            "document_type": "Command",
            "document_format": "JSON",
            "latest_version": "2",
            "content": json.dumps(body),
        },
        "each.value": {
            "instance": {
                "id": "i-12345678",
                "arn": "arn:aws:ec2:us-east-1:123456789012:instance/i-12345678",
                "profile_arn": "arn:aws:iam::123456789012:instance-profile/runtime-secrets-123",
            },
            "utc_hour": 3,
            "utc_minute": 0,
            "apply_immediately": False,
            "parameters": {},
        },
        "local.ssm_association_document": body,
        "local.ssm_association_parameters": {},
        "data.aws_partition.ssm_associations.partition": "aws",
        "data.aws_region.ssm_associations.region": "us-east-1",
        "data.aws_caller_identity.ssm_associations.account_id": "123456789012",
    }


def test_native_document_target_profile_and_version_ownership():
    tree = generate(architecture())
    association = resources(tree, "aws_ssm_association")[0]
    assert association["name"] == "${aws_ssm_document.source-resource.name}"
    assert (
        association["document_version"]
        == "${aws_ssm_document.source-resource.latest_version}"
    )
    assert association["for_each"] == "${var.ec2_associations}"
    assert association["targets"][0]["key"] == "InstanceIds"
    assert association["targets"][0]["values"] == ["${each.value.instance.id}"]
    assert (
        association["apply_only_at_cron_interval"] == "${!each.value.apply_immediately}"
    )
    assert association["max_concurrency"] == "1" and association["max_errors"] == "0"
    assert "automation_target_parameter_name" not in association
    assert "wait_for_success_timeout_seconds" not in association
    assert len(association["lifecycle"][0]["precondition"]) == 5
    instance = resources(tree, "aws_instance")[0]
    assert (
        instance["iam_instance_profile"]
        == "${aws_iam_instance_profile.runtime_secrets.name}"
    )
    assert instance["depends_on"] == ["${aws_iam_role_policy_attachment.ssm_core}"]
    assert "user_data" not in instance
    assert (
        len(resources(tree, "aws_iam_role"))
        == len(resources(tree, "aws_iam_instance_profile"))
        == 1
    )
    attachment = resources(tree, "aws_iam_role_policy_attachment")[0]
    assert attachment["role"] == "${aws_iam_role.target-resource_role.name}"
    assert "AmazonSSMManagedInstanceCore" in attachment["policy_arn"]
    outputs = file_with(tree, "/target-resource/outputs.tf")
    assert "aws_instance.target-resource.arn" in outputs
    assert "aws_iam_instance_profile.runtime_secrets.arn" in outputs
    assert "module.source-resource" not in outputs
    result = ConnectionProcessor().process_all(project(architecture()))
    assert {(r.module, r.filename) for r in result.resources} == {
        ("source-resource", "ec2_associations.tf"),
        ("target-resource", "runtime_secrets_role.tf"),
        ("target-resource", "ssm_node.tf"),
    }
    assert not result.iam


@given(
    name=resource_name_st,
    hour=st.integers(0, 23),
    minute=st.integers(0, 59),
    immediate=st.booleans(),
    duplicates=st.integers(1, 4),
)
@settings(max_examples=20, deadline=None)
def test_property_schedule_names_and_duplicates(
    name, hour, minute, immediate, duplicates
):
    payload = architecture()
    payload["resources"][1]["name"] = "target-" + name
    payload["connections"][0].update(
        target="target-" + name,
        connection_config={
            "utc_hour": hour,
            "utc_minute": minute,
            "apply_immediately": immediate,
        },
    )
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * duplicates))
    assert generate(payload) == expected
    assert len(resources(expected, "aws_ssm_association")) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("utc_hour", -1),
        ("utc_hour", 24),
        ("utc_hour", 3.0),
        ("utc_hour", "3"),
        ("utc_hour", True),
        ("utc_minute", 60),
        ("utc_minute", -1),
        ("utc_minute", None),
        ("apply_immediately", "false"),
        ("apply_immediately", 0),
        ("parameters_json", "[]"),
        ("parameters_json", "not json"),
        ("parameters_json", '{"Message":123}'),
        ("parameters_json", '{"Message":null}'),
        ("parameters_json", '{"Message":[]}'),
        ("parameters_json", '{"Bad-Key":"x"}'),
        ("parameters_json", '{"Message":"one","Message":"two"}'),
        ("parameters_json", '{"Message":NaN}'),
        ("instance_id", "*"),
        ("schedule_expression", "rate(1 minute)"),
        ("document_version", "$LATEST"),
        ("parameters_json", json.dumps({"Message": "x" * 32769})),
    ],
)
def test_invalid_config_is_rejected(field, value):
    with pytest.raises(ValidationError):
        SsmEc2Config.model_validate({field: value})
    payload = architecture()
    payload["connections"][0]["connection_config"] = {field: value}
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("document_type", "Automation"),
        ("document_type", "Policy"),
        ("document_name", "bad/name"),
        ("document_name", "ab"),
        ("content", "[]"),
        ("content", "{"),
        ("content", '{"schemaVersion":"2.2","mainSteps":[]}'),
        ("content", '{"schemaVersion":"2.0","mainSteps":[]}'),
        (
            "content",
            '{"schemaVersion":"2.2","mainSteps":[{"name":"Step","action":"aws:runShellScript","inputs":{} }],"extra": NaN}',
        ),
    ],
)
def test_incompatible_documents_fail_generation_and_preview(field, value):
    payload = architecture()
    payload["resources"][0]["config"][field] = value
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)
    with pytest.raises(InvalidConnectionConfigError):
        ConnectionPreviewer().preview_all(project(payload))


@pytest.mark.parametrize(
    "mutation",
    [
        "step_name",
        "duplicate_step",
        "inputs",
        "action",
        "steps_object",
        "parameters_list",
        "parameter_type",
        "default_string",
        "default_list",
    ],
)
def test_document_structure_is_checked(mutation):
    payload = architecture()
    body = document(payload)
    if mutation == "step_name":
        body["mainSteps"][0]["name"] = "bad name"
    elif mutation == "duplicate_step":
        body["mainSteps"].append(deepcopy(body["mainSteps"][0]))
    elif mutation == "inputs":
        body["mainSteps"][0]["inputs"] = []
    elif mutation == "action":
        body["mainSteps"][0]["action"] = "arbitrary"
    elif mutation == "steps_object":
        body["mainSteps"] = {"Step": body["mainSteps"][0]}
    elif mutation == "parameters_list":
        body["parameters"] = []
    else:
        body["parameters"] = {
            "Message": {
                "type": "Integer"
                if mutation == "parameter_type"
                else "String"
                if mutation == "default_string"
                else "StringList",
                "default": 1,
            }
        }
    payload["resources"][0]["config"]["content"] = json.dumps(body)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize(
    "parameters",
    [{}, {"Unknown": "x"}, {"Commands": "echo"}, {"Message": "x", "Commands": "echo"}],
)
def test_required_unknown_and_list_overrides_are_rejected(parameters):
    payload = architecture()
    with_parameters(payload)
    payload["connections"][0]["connection_config"] = {
        "parameters_json": json.dumps(parameters)
    }
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize(
    "field,value", [("utc_hour", 4), ("utc_minute", 1), ("apply_immediately", True)]
)
def test_conflicting_duplicate_settings_are_rejected(field, value):
    payload = architecture()
    edge = deepcopy(payload["connections"][0])
    edge["connection_config"] = {field: value}
    payload["connections"].append(edge)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_target_specific_settings_and_stable_pair_identity():
    payload = architecture()
    edge = deepcopy(payload["connections"][0])
    node = dict(deepcopy(payload["resources"][1]), name="other-node", id="other-node")
    payload["resources"].append(node)
    edge.update(
        target=node["name"], target_id=node["id"], connection_config={"utc_hour": 4}
    )
    payload["connections"].append(edge)
    original = ConnectionProcessor().process_all(project(payload))
    settings = next(i.value for i in original.inputs if i.name == "ec2_associations")
    assert settings.count("module.") == 2
    assert "utc_hour = 4" in settings
    payload["connections"].reverse()
    assert generate(payload) == generate(
        dict(payload, connections=list(reversed(payload["connections"])))
    )
    payload["resources"][1]["name"] = "renamed-node"
    payload["connections"][1]["target"] = "renamed-node"
    renamed = ConnectionProcessor().process_all(project(payload))
    value = next(i.value for i in renamed.inputs if i.name == "ec2_associations")
    assert settings.replace("module.target-resource", "module.renamed-node") == value


def test_effective_regions_and_user_data_are_preserved():
    payload = architecture()
    payload["resources"][1]["provider_region"] = "eu-west-1"
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)
    payload["environments"][0]["variables"]["region"] = "eu-central-1"
    payload["resources"][1]["config"]["user_data"] = '#!/bin/bash\necho "${HOSTNAME}"\n'
    connected = generate(payload)
    payload["connections"] = []
    standalone = generate(payload)
    assert (
        resources(connected, "aws_instance")[0]["user_data"]
        == resources(standalone, "aws_instance")[0]["user_data"]
    )
    assert not resources(standalone, "aws_iam_instance_profile")
    assert resources(connected, "aws_ssm_document") == resources(
        standalone, "aws_ssm_document"
    )


def test_yaml_document_and_literals_are_preserved():
    payload = architecture()
    with_parameters(payload)
    payload["resources"][0]["config"]["content"] = yaml.safe_dump(document(payload))
    payload["resources"][0]["config"]["document_format"] = "YAML"
    tree = generate(payload)
    main = file_with(tree, "/environments/dev/main.tf")
    assert "$${operator}" in main and "%%{literal}" in main
    assert len(resources(tree, "aws_ssm_association")) == 1


@pytest.mark.parametrize("parameter_type", [[], {}, None])
def test_untyped_parameter_declarations_raise_domain_errors(parameter_type):
    payload = architecture()
    body = document(payload)
    body["parameters"] = {"Message": {"type": parameter_type}}
    payload["resources"][0]["config"]["content"] = json.dumps(body)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_yaml_aliases_and_combined_payload_limits_are_rejected():
    payload = architecture()
    payload["resources"][0]["config"].update(
        document_format="YAML",
        content="schemaVersion: '2.2'\nmainSteps: &steps [*steps]\n",
    )
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)
    payload = architecture()
    with_parameters(payload)
    body = document(payload)
    body["description"] = "x" * 40000
    payload["resources"][0]["config"]["content"] = json.dumps(body)
    payload["connections"][0]["connection_config"]["parameters_json"] = json.dumps(
        {"Message": "x" * 30000}
    )
    with pytest.raises(InvalidConnectionConfigError, match="together"):
        generate(payload)


def test_preview_explains_execution_permissions_and_provider_limits():
    issue = ConnectionPreviewer().preview_all(project(architecture()))[0].issues[0]
    assert issue.severity == "warning"
    for text in [
        "03:00 UTC",
        "next scheduled",
        "Parameter Store",
        "SSM Agent",
        "does not wait",
        "dispatch",
        "deletion does not undo",
        "state",
    ]:
        assert text in issue.message


@needs_terraform
@pytest.mark.parametrize(
    "index,field,value",
    [
        (0, "document_type", "Automation"),
        (0, "arn", "arn:aws:ssm:eu-west-1:123456789012:document/managed-document"),
        (0, "arn", "arn:aws:ssm:us-east-1:999999999999:document/managed-document"),
        (0, "name", "*"),
        (0, "latest_version", "$LATEST"),
        (1, "id", "*"),
        (1, "arn", "arn:aws:ec2:eu-west-1:123456789012:instance/i-12345678"),
        (1, "profile_arn", "arn:aws:iam::999999999999:instance-profile/profile"),
        (2, "utc_hour", 24),
        (2, "utc_hour", 3.5),
        (2, "utc_minute", 60),
        (2, "utc_minute", 0.5),
        (3, "schemaVersion", "2.0"),
        (3, "mainSteps", []),
        (3, "document_format", "TEXT"),
        (4, "parameters", {"Unknown": "x"}),
    ],
)
def test_native_scope_and_schedule_guards(tmp_path, index, field, value):
    values = native_values()
    if index == 0 or field == "document_format":
        values["aws_ssm_document.document"][field] = value
    elif index == 1:
        values["each.value"]["instance"][field] = value
    elif index == 3:
        values["local.ssm_association_document"][field] = value
    else:
        values["each.value"][field] = value
    assert (
        evaluate(
            tmp_path,
            str(
                association_preconditions("aws_ssm_document.document")[index][
                    "condition"
                ]
            ),
            values,
        )
        is False
    )


@needs_terraform
@pytest.mark.parametrize(
    "partition,region", [("aws", "us-east-1"), ("aws-cn", "cn-north-1")]
)
def test_native_guards_accept_matching_scope_and_schedule(tmp_path, partition, region):
    values = native_values()
    native = values["aws_ssm_document.document"]
    native["arn"] = (
        f"arn:{partition}:ssm:{region}:123456789012:document/managed-document"
    )
    values["each.value"]["instance"].update(
        arn=f"arn:{partition}:ec2:{region}:123456789012:instance/i-12345678",
        profile_arn=f"arn:{partition}:iam::123456789012:instance-profile/profile",
    )
    values["data.aws_partition.ssm_associations.partition"] = partition
    values["data.aws_region.ssm_associations.region"] = region
    assert (
        evaluate(
            tmp_path,
            " && ".join(
                f"({p['condition']})"
                for p in association_preconditions("aws_ssm_document.document")
            ),
            values,
        )
        is True
    )
    schedule = re.search(
        r"  schedule_expression = (.*)\n",
        file_with(generate(architecture()), "/ec2_associations.tf"),
    )[1]
    assert evaluate(tmp_path, schedule, values) == "cron(0 3 ? * * *)"


@needs_terraform
def test_emitted_parameters_preserve_literal_templates(tmp_path):
    payload = architecture()
    with_parameters(payload)
    contribution = ConnectionProcessor().process_all(project(payload))
    settings = next(
        i.value for i in contribution.inputs if i.name == "ec2_associations"
    )
    values = evaluate(
        tmp_path,
        settings,
        {"module.target-resource.ssm_node": native_values()["each.value"]["instance"]},
    )
    assert next(iter(values.values()))["parameters"] == {
        "Message": "Hello ${operator}, %{literal}\nSecond line"
    }


@needs_terraform
def test_native_required_parameters_guard(tmp_path):
    values = native_values()
    condition = str(
        association_preconditions("aws_ssm_document.document")[4]["condition"]
    )
    values["local.ssm_association_parameters"] = {"Message": {"type": "String"}}
    assert evaluate(tmp_path, condition, values) is False
    values["each.value"]["parameters"] = {"Message": "hello"}
    assert evaluate(tmp_path, condition, values) is True
    values["local.ssm_association_parameters"]["Message"]["type"] = "StringList"
    assert evaluate(tmp_path, condition, values) is False


@pytest.mark.terraform
@needs_terraform
@pytest.mark.parametrize(
    "mode",
    [
        "plain",
        "duplicate",
        "parameters",
        "yaml",
        "immediate",
        "two_instances",
        "shared_node",
        "regional",
        "efs_secrets",
    ],
)
def test_generated_projects_validate_and_have_acyclic_graphs(tmp_path, mode):
    payload = architecture()
    if mode == "duplicate":
        payload["connections"].append(deepcopy(payload["connections"][0]))
    elif mode in {"parameters", "yaml"}:
        with_parameters(payload)
        if mode == "yaml":
            payload["resources"][0]["config"].update(
                document_format="YAML", content=yaml.safe_dump(document(payload))
            )
    elif mode == "immediate":
        payload["connections"][0]["connection_config"] = {
            "apply_immediately": True,
            "utc_hour": 23,
            "utc_minute": 59,
        }
    elif mode == "two_instances":
        payload["resources"].append(
            dict(deepcopy(payload["resources"][1]), name="other", id="other")
        )
        payload["connections"].append(
            dict(
                payload["connections"][0],
                target="other",
                target_id="other",
                connection_config={"utc_hour": 4},
            )
        )
    elif mode == "shared_node":
        other = dict(
            deepcopy(payload["resources"][0]),
            name="other-document",
            id="other-document",
        )
        other["config"]["document_name"] = "other-document"
        payload["resources"].append(other)
        payload["connections"].append(
            dict(payload["connections"][0], source=other["name"], source_id=other["id"])
        )
    elif mode == "regional":
        for instance in payload["resources"]:
            instance["provider_region"] = "eu-west-1"
    elif mode == "efs_secrets":
        mixed = efs_architecture()
        source = payload["resources"][0]
        mixed["resources"].append(dict(source, name="document", id="document"))
        mixed["connections"].append(
            dict(
                payload["connections"][0],
                source="document",
                source_id="document",
                target_id="tgt",
            )
        )
        payload = mixed
        tree = generate(payload)
        assert (
            len(resources(tree, "aws_iam_role"))
            == len(resources(tree, "aws_iam_instance_profile"))
            == 1
        )
        dependencies = resources(tree, "aws_instance")[0]["depends_on"]
        assert set(dependencies) == {
            "${aws_iam_role_policy.runtime_secrets}",
            "${aws_iam_role_policy.efs_mounts}",
            "${aws_iam_role_policy_attachment.ssm_core}",
        }
    tree = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    _write_tree(tmp_path, tree)
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
