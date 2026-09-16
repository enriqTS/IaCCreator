"""Destination naming preserves explicit source selection and valid unique rules."""

import json
import subprocess

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.generators.dms_table_mappings import table_mapping_rules
from app.models.connection_configs.dms_task import DmsReplicationTaskConfig
from app.models.input_models import ServiceType
from tests.test_database_access_connections import generate
from tests.test_dms_replication_task_connections import architecture, task_config
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)


@given(
    tables=st.lists(
        st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,15}", fullmatch=True),
        min_size=1,
        max_size=10,
        unique=True,
    ),
    prefix=st.from_regex(r"[A-Za-z_][A-Za-z0-9_]{0,10}", fullmatch=True),
)
def test_transformations_preserve_selection_and_unique_rule_ids(tables, prefix):
    config = task_config(architecture())
    config.update(
        table_names=",".join(tables),
        target_schema="archive",
        target_table_prefix=prefix,
    )
    rules = table_mapping_rules(DmsReplicationTaskConfig.model_validate(config))
    selection = [rule for rule in rules if rule["rule-type"] == "selection"]
    assert [rule["object-locator"]["table-name"] for rule in selection] == sorted(
        tables
    )
    assert all(rule["rule-action"] == "explicit" for rule in selection)
    assert len({rule["rule-id"] for rule in rules}) == len(tables) + 2
    assert rules[-2] == {
        "rule-type": "transformation",
        "rule-id": str(len(tables) + 1),
        "rule-name": str(len(tables) + 1),
        "rule-action": "rename",
        "rule-target": "schema",
        "object-locator": {"schema-name": "public"},
        "value": "archive",
    }
    assert rules[-1]["rule-action"] == "add-prefix"
    assert rules[-1]["rule-target"] == "table"
    assert rules[-1]["object-locator"] == {"schema-name": "public", "table-name": "%"}
    assert rules[-1]["value"] == prefix
    config["table_names"] = ",".join(reversed(tables + tables))
    assert table_mapping_rules(DmsReplicationTaskConfig.model_validate(config)) == rules


@pytest.mark.parametrize("field", ["target_schema", "target_table_prefix"])
@pytest.mark.parametrize("value", ["%", "a-b", "${value}", "123name", "a" * 64, " "])
def test_invalid_destination_names_are_rejected(field, value):
    config = task_config(architecture())
    config[field] = value
    with pytest.raises(ValidationError):
        DmsReplicationTaskConfig.model_validate(config)


def test_prefixed_names_cannot_exceed_portable_identifier_limit():
    config = task_config(architecture())
    config.update(table_names="a" * 62, target_table_prefix="x")
    assert DmsReplicationTaskConfig.model_validate(config)
    config["target_table_prefix"] = "xx"
    with pytest.raises(ValidationError, match="63 characters"):
        DmsReplicationTaskConfig.model_validate(config)


def test_empty_optional_fields_and_unchanged_schema_preserve_legacy_output():
    payload = architecture()
    expected = generate(payload)
    task_config(payload).update(target_schema="", target_table_prefix="")
    assert generate(payload) == expected
    task_config(payload)["target_schema"] = "public"
    assert generate(payload) == expected


@needs_terraform
@pytest.mark.parametrize("target", [ServiceType.RDS, ServiceType.AURORA])
@pytest.mark.parametrize(
    "options",
    [
        {"target_schema": "archive"},
        {"target_table_prefix": "copy_"},
        {"target_schema": "archive", "target_table_prefix": "copy_"},
    ],
)
def test_transformed_task_validates_and_mapping_json_evaluates(
    target, options, tmp_path
):
    payload = architecture(target)
    task_config(payload).update(options)
    tree = generate(payload)
    _write_tree(tmp_path, tree)
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
    task = next(v for v in tree.values() if 'resource "aws_dms_replication_task"' in v)
    expression = task.split("table_mappings = ", 1)[1].split(
        "\n  replication_task_settings = ", 1
    )[0]
    (tmp_path / "main.tf").write_text("locals {\n  mapping = " + expression + "\n}\n")
    evaluated = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input="local.mapping\n",
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert evaluated.returncode == 0, evaluated.stderr
    mapping = json.loads(json.loads(evaluated.stdout))
    selections = [r for r in mapping["rules"] if r["rule-type"] == "selection"]
    assert {r["object-locator"]["table-name"] for r in selections} == {
        "customers",
        "orders",
    }
    assert len(mapping["rules"]) == 2 + len(options)
