"""Full-load tasks resolve managed endpoints and preserve explicit table selection."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.dms_task import DmsReplicationTaskConfig
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.test_database_access_connections import generate
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)


def architecture(target=ServiceType.RDS):
    return connection_architecture(
        resolve_spec(
            ServiceType.DATABASE_MIGRATION_SERVICE, target, "replication_task", {}
        )
    )


def task_config(payload):
    return payload["connections"][2]["connection_config"]


@given(
    target=st.sampled_from([ServiceType.RDS, ServiceType.AURORA]),
    tables=st.lists(
        st.from_regex(r"[A-Za-z][A-Za-z0-9]{0,15}", fullmatch=True),
        min_size=1,
        max_size=10,
        unique=True,
    ),
)
def test_task_references_native_resources_and_explicit_tables(target, tables):
    payload = architecture(target)
    task_config(payload)["table_names"] = ", ".join(tables)
    tree = generate(payload)
    tasks = [
        (k, v) for k, v in tree.items() if 'resource "aws_dms_replication_task"' in v
    ]
    assert len(tasks) == 1
    path, text = tasks[0]
    assert "/source-resource/" in path
    assert 'migration_type = "full-load"' in text
    assert "start_replication_task = false" in text
    assert 'TargetTablePrepMode = "DO_NOTHING"' in text
    assert (
        "replication_instance_arn = aws_dms_replication_instance.source-resource.replication_instance_arn"
        in text
    )
    assert "source_endpoint_arn = aws_dms_endpoint.endpoint_" in text
    assert "target_endpoint_arn = aws_dms_endpoint.endpoint_" in text
    assert text.count('rule-action = "explicit"') == len(tables)
    for table in tables:
        assert f'table-name = "{table}"' in text
    assert 'schema-name = "public"' in text
    assert "DROP_AND_CREATE" not in text
    assert "password" not in text
    assert "replication_task_arn" in "\n".join(tree.values())
    task_config(payload)["table_names"] = ",".join(reversed(tables + tables))
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "field,value",
    [
        ("task_id", "bad--id"),
        ("task_id", "bad-"),
        ("task_id", "2bad"),
        ("source_endpoint_id", "bad/id"),
        ("target_endpoint_id", ""),
        ("table_schema", "%"),
        ("table_schema", "${schema}"),
        ("table_names", ""),
        ("table_names", "one,,two"),
        ("table_names", "orders,%"),
        ("table_names", "orders.*"),
        ("table_names", "${var.table}"),
        ("table_names", ",".join(f"table{i}" for i in range(101))),
    ],
)
def test_invalid_task_config_is_rejected(field, value):
    config = task_config(architecture())
    config[field] = value
    with pytest.raises(ValidationError):
        DmsReplicationTaskConfig.model_validate(config)


def test_schema_exposes_required_fields_without_execution_or_secret_settings():
    fields = DmsReplicationTaskConfig.get_field_schema()
    assert {field.key for field in fields if field.required} == {
        "task_id",
        "source_endpoint_id",
        "target_endpoint_id",
        "table_schema",
        "table_names",
    }
    assert {field.key for field in fields if not field.required} == {
        "target_schema",
        "target_table_prefix",
    }
    config = task_config(architecture())
    for field in ("migration_type", "password", "start_replication_task"):
        with pytest.raises(ValidationError):
            DmsReplicationTaskConfig.model_validate({**config, field: "unsafe"})


@pytest.mark.parametrize("missing", [0, 1])
def test_missing_endpoints_are_rejected(missing):
    payload = architecture()
    del payload["connections"][missing]
    with pytest.raises(InvalidConnectionConfigError, match="requires a"):
        generate(payload)


def test_task_cannot_use_an_endpoint_on_another_replication_instance():
    payload = architecture()
    instance = deepcopy(payload["resources"][0])
    instance.update(id="other", name="other-dms")
    payload["resources"].append(instance)
    payload["connections"][1].update(source="other-dms", source_id="other")
    with pytest.raises(InvalidConnectionConfigError, match="on this DMS instance"):
        generate(payload)


def test_task_target_must_match_its_endpoint_database():
    payload = architecture()
    payload["connections"][2].update(target="origin-database", target_id="origin")
    with pytest.raises(InvalidConnectionConfigError, match="task's target database"):
        generate(payload)


def test_source_and_target_cannot_be_the_same_database():
    payload = architecture()
    payload["connections"][1].update(target="target-resource", target_id="tgt")
    with pytest.raises(InvalidConnectionConfigError, match="different databases"):
        generate(payload)


@pytest.mark.parametrize(
    "field,value", [("table_names", "other_table"), ("table_schema", "other_schema")]
)
def test_conflicting_task_ids_are_rejected(field, value):
    payload = architecture()
    second = deepcopy(payload["connections"][2])
    second["connection_config"][field] = value
    payload["connections"].append(second)
    with pytest.raises(InvalidConnectionConfigError, match="unique"):
        generate(payload)


def test_multiple_tasks_share_endpoints_and_keep_distinct_mappings():
    payload = architecture()
    second = deepcopy(payload["connections"][2])
    second["connection_config"].update(task_id="another-task", table_names="products")
    payload["connections"].append(second)
    tree = generate(payload)
    text = "\n".join(tree.values())
    assert text.count('resource "aws_dms_replication_task"') == 2
    assert text.count('resource "aws_dms_endpoint"') == 2
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


def test_identifiers_normalize_and_preview_explains_start_behavior():
    payload = architecture()
    expected = generate(payload)
    for field in ("task_id", "source_endpoint_id", "target_endpoint_id"):
        task_config(payload)[field] = task_config(payload)[field].upper()
    assert generate(payload) == expected
    project = IRBuilder().build(ArchitectureDescription.model_validate(payload))
    preview = ConnectionPreviewer().preview_all(project)[2]
    assert any(
        resource.resource_type == "aws_dms_replication_task"
        for resource in preview.resources
    )
    assert any("later apply can stop" in issue.message for issue in preview.issues)


@needs_terraform
@pytest.mark.parametrize("target", [ServiceType.RDS, ServiceType.AURORA])
def test_task_project_validates_and_has_no_dependency_cycles(target, tmp_path):
    payload = architecture(target)
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
