"""Table access grants distinguish application records from service metadata."""

import json
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.models.connection_configs.table_access import (
    KeyspacesTableAccessConfig,
    TimestreamTableAccessConfig,
)
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)

TARGETS = [ServiceType.KEYSPACES, ServiceType.TIMESTREAM]
SOURCES = [ServiceType.LAMBDA, ServiceType.ECS]


def architecture(
    source=ServiceType.LAMBDA, target=ServiceType.KEYSPACES, kind="reads_from"
):
    return connection_architecture(resolve_spec(source, target, kind, {}))


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


def generate(payload):
    return CodeGenerator().generate(project(payload))


@given(
    source=st.sampled_from(SOURCES),
    target=st.sampled_from(TARGETS),
    kind=st.sampled_from(["reads_from", "writes_to"]),
    table=st.from_regex(r"[a-z][a-z0-9_]{2,25}", fullmatch=True),
)
def test_data_and_metadata_permissions_have_separate_scopes(
    source, target, kind, table
):
    payload = architecture(source, target, kind)
    payload["connections"][0]["connection_config"]["table_name"] = table
    tree = generate(payload)
    policy = json.loads(
        tree["connection-check/iam-policies/source-resource-policy.json"]
    )
    data = [s for s in policy["Statement"] if "_table_arn}" in str(s["Resource"])]
    assert len(data) == 1
    assert data[0]["Resource"].startswith("${var.table_access_")
    assert "*" not in data[0]["Resource"]
    if target == ServiceType.KEYSPACES:
        assert data[0]["Action"] == (
            ["cassandra:Select"] if kind == "reads_from" else ["cassandra:Modify"]
        )
        metadata = [
            s for s in policy["Statement"] if "_system_arn}" in str(s["Resource"])
        ]
        assert len(metadata) == 1 and metadata[0]["Action"] == ["cassandra:Select"]
    else:
        assert set(data[0]["Action"]) == {
            "timestream:Select" if kind == "reads_from" else "timestream:WriteRecords",
            "timestream:DescribeTable",
        }
        discovery = [
            s
            for s in policy["Statement"]
            if s["Action"] == ["timestream:DescribeEndpoints"]
        ]
        assert discovery == [
            {
                "Effect": "Allow",
                "Action": ["timestream:DescribeEndpoints"],
                "Resource": "*",
            }
        ]
    text = "\n".join(tree.values())
    assert f'table_name = "{table}"' in text
    assert "database_name = var.table_access_" in text
    assert "region = var.table_access_" in text
    assert 'resource "aws_keyspaces_table"' not in text
    assert 'resource "aws_timestreamwrite_table"' not in text
    assert "secretsmanager:GetSecretValue" not in text
    if source == ServiceType.ECS:
        assert "task_role_arn = aws_iam_role.source-resource_role.arn" in text
    assert ConnectionPreviewer().preview_all(project(payload))[0].issues


@pytest.mark.parametrize(
    "model", [KeyspacesTableAccessConfig, TimestreamTableAccessConfig]
)
@pytest.mark.parametrize("table", ["", "*", "data/*", "data?", "${all}", "a" * 257])
def test_table_selector_cannot_expand_iam_scope(model, table):
    with pytest.raises(ValidationError):
        model(table_name=table)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("source", SOURCES)
def test_multiple_tables_and_access_modes_are_deterministic(source, target):
    payload = architecture(source, target)
    for table, kind in [
        ("application_data", "writes_to"),
        ("audit_records", "reads_from"),
    ]:
        connection = deepcopy(payload["connections"][0])
        connection["connection_config"]["table_name"] = table
        connection["connection_type"] = kind
        payload["connections"].append(connection)
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected
    policy = json.loads(
        expected["connection-check/iam-policies/source-resource-policy.json"]
    )
    assert (
        len([s for s in policy["Statement"] if "_table_arn}" in str(s["Resource"])])
        == 3
    )
    assert (
        len(
            [
                s
                for s in policy["Statement"]
                if s["Action"] == ["timestream:DescribeEndpoints"]
                or "_system_arn}" in str(s["Resource"])
            ]
        )
        == 1
    )


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("source", SOURCES)
def test_default_access_is_read_only_and_table_is_required(source, target):
    spec = resolve_spec(source, target, None, {})
    assert spec.connection_type == "reads_from"
    with pytest.raises(ValidationError):
        spec.config_model()
    schema = spec.config_model.get_field_schema()
    assert schema[0].key == "table_name" and schema[0].required


@needs_terraform
@pytest.mark.parametrize("target", TARGETS)
def test_table_arn_and_metadata_evaluate_with_target_identity(target, tmp_path):
    payload = architecture(target=target)
    ir = project(payload)
    spec = resolve_spec(ServiceType.LAMBDA, target, "reads_from", {})
    result = spec.handler.handle(ir.connections[0], ir)
    resource = f"{spec.handler.resource_type}.target-resource"
    suffix = (
        "/keyspace/application/"
        if target == ServiceType.KEYSPACES
        else "database/application"
    )
    service = "cassandra" if target == ServiceType.KEYSPACES else "timestream"
    prefix = f"arn:aws-us-gov:{service}:us-gov-west-1:987654321098:"
    arn = prefix + suffix
    values = {
        o.name: o.value.replace(resource + ".arn", json.dumps(arn))
        for o in result.outputs
        if o.module == "target-resource"
        and (o.name.endswith("_arn") or o.name.endswith("_region"))
    }
    expression = (
        "jsonencode({"
        + ", ".join(f'"{key}" = {value}' for key, value in values.items())
        + "})"
    )
    process = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input=expression + "\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert process.returncode == 0, process.stderr
    evaluated = json.loads(json.loads(process.stdout))
    table_arn = next(
        value for key, value in evaluated.items() if key.endswith("_table_arn")
    )
    assert table_arn == arn.rstrip("/") + "/table/application_data"
    assert (
        next(value for key, value in evaluated.items() if key.endswith("_region"))
        == "us-gov-west-1"
    )
    if target == ServiceType.KEYSPACES:
        assert evaluated["client_system_keyspaces_arn"] == prefix + "/keyspace/system*"


@needs_terraform
@pytest.mark.parametrize("target", TARGETS)
def test_table_connections_validate_without_dependency_cycles(target, tmp_path):
    payload = architecture(ServiceType.ECS, target)
    write = deepcopy(payload["connections"][0])
    write["connection_type"] = "writes_to"
    payload["connections"].append(write)
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
