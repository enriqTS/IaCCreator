"""CDC modes preserve explicit start points and engine-specific IAM restrictions."""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.dms_task import DmsReplicationTaskConfig
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.connection_previewer import ConnectionPreviewer
from app.services.ir_builder import IRBuilder
from tests.test_database_access_connections import generate
from tests.test_dms_replication_task_connections import architecture, task_config
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)

SOURCES = [
    (ServiceType.RDS, "mysql"),
    (ServiceType.RDS, "mariadb"),
    (ServiceType.AURORA, "aurora-mysql"),
]


def cdc_architecture(
    source_type=ServiceType.RDS, engine="mysql", mode="cdc", target=ServiceType.RDS
):
    payload = architecture(target)
    origin = architecture(source_type)["resources"][2]
    origin["config"]["engine"] = engine
    payload["resources"][2] = origin
    task_config(payload)["migration_type"] = mode
    if mode == "cdc":
        task_config(payload)["cdc_start_position"] = "mysql-bin-changelog.000024:373"
    return payload


@given(
    source=st.sampled_from(SOURCES),
    mode=st.sampled_from(["cdc", "full-load-and-cdc"]),
    target=st.sampled_from([ServiceType.RDS, ServiceType.AURORA]),
    position=st.integers(min_value=4, max_value=2**48),
)
def test_cdc_uses_selected_mode_start_position_and_source_engine_guard(
    source, mode, target, position
):
    payload = cdc_architecture(*source, mode, target)
    if mode == "cdc":
        task_config(payload)["cdc_start_position"] = f"mysql-bin.000001:{position}"
    tree = generate(payload)
    task = next(v for v in tree.values() if 'resource "aws_dms_replication_task"' in v)
    assert f'migration_type = "{mode}"' in task
    assert "start_replication_task = false" in task
    assert "var.dms_database_origin-database_engine" in task
    assert 'contains(["mysql", "mariadb", "aurora-mysql"]' in task
    assert "source_endpoint_arn = aws_dms_endpoint." in task
    assert "target_endpoint_arn = aws_dms_endpoint." in task
    if mode == "cdc":
        assert f'cdc_start_position = "mysql-bin.000001:{position}"' in task
        assert "FullLoadSettings" not in task
    else:
        assert "cdc_start_position" not in task
        assert 'TargetTablePrepMode = "DO_NOTHING"' in task


@pytest.mark.parametrize(
    "source_type,engine",
    [(ServiceType.RDS, "postgres"), (ServiceType.AURORA, "aurora-postgresql")],
)
@pytest.mark.parametrize("mode", ["cdc", "full-load-and-cdc"])
def test_postgresql_iam_sources_reject_replication_modes(source_type, engine, mode):
    with pytest.raises(
        InvalidConnectionConfigError, match="PostgreSQL IAM replication"
    ):
        generate(cdc_architecture(source_type, engine, mode))


@pytest.mark.parametrize(
    "mode,position",
    [
        ("cdc", None),
        ("cdc", ""),
        ("full-load", "mysql-bin.000001:4"),
        ("full-load-and-cdc", "mysql-bin.000001:4"),
        ("invalid", None),
        ("cdc", "2026-09-16T00:00:00Z"),
        ("cdc", "checkpoint:V1#1"),
        ("cdc", "mysql-bin.000001:-1"),
        ("cdc", "mysql-bin.000001:1.2"),
        ("cdc", "${var.position}"),
        ("cdc", "mysql-bin.000001:4\n"),
    ],
)
def test_invalid_cdc_combinations_are_rejected(mode, position):
    config = task_config(architecture())
    config.update(migration_type=mode, cdc_start_position=position)
    with pytest.raises(ValidationError):
        DmsReplicationTaskConfig.model_validate(config)


def test_empty_position_preserves_default_full_load():
    payload = architecture()
    expected = generate(payload)
    task_config(payload)["cdc_start_position"] = ""
    assert generate(payload) == expected


def test_cdc_preview_exposes_external_prerequisites():
    payload = cdc_architecture()
    project = IRBuilder().build(ArchitectureDescription.model_validate(payload))
    message = ConnectionPreviewer().preview_all(project)[2].issues[0].message
    assert "ROW binlogging" in message and "replication SQL grants" in message
    assert "consistent with the chosen binlog position" in message
    assert "later apply can stop" in message


@needs_terraform
@pytest.mark.parametrize("source_type,engine", SOURCES)
@pytest.mark.parametrize("mode", ["cdc", "full-load-and-cdc"])
def test_cdc_projects_validate_without_cycles(source_type, engine, mode, tmp_path):
    payload = cdc_architecture(source_type, engine, mode, ServiceType.AURORA)
    task_config(payload).update(target_schema="archive", target_table_prefix="copy_")
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
