"""SQL Server CDC requires native LSNs and guarded transaction-log backup support."""

import json
import subprocess

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.dms_task import DmsReplicationTaskConfig
from app.models.input_models import ArchitectureDescription
from app.services.connection_previewer import ConnectionPreviewer
from app.services.ir_builder import IRBuilder
from tests.test_database_access_connections import generate
from tests.test_dms_cdc_tasks import cdc_architecture
from tests.test_dms_postgres_cdc import postgres_architecture
from tests.test_dms_replication_task_connections import task_config
from tests.test_dms_sqlserver_connections import (
    EDITIONS,
    sqlserver_migration,
    validate_project,
)
from tests.test_generated_project_validates import needs_terraform


def sqlserver_cdc(engine="sqlserver-se", mode="cdc", version="3.5.3"):
    payload = sqlserver_migration(engine, True)
    payload["resources"][0]["config"]["engine_version"] = version
    task_config(payload)["migration_type"] = mode
    if mode == "cdc":
        task_config(payload)["cdc_start_position"] = "00000014:00000061:0001"
    return payload


@given(
    engine=st.sampled_from(EDITIONS),
    mode=st.sampled_from(["cdc", "full-load-and-cdc"]),
    vlf=st.integers(min_value=0, max_value=2**32 - 1),
    offset=st.integers(min_value=0, max_value=2**32 - 1),
    slot=st.integers(min_value=1, max_value=2**16 - 1),
)
def test_sqlserver_cdc_uses_native_positions_and_guards(
    engine, mode, vlf, offset, slot
):
    payload = sqlserver_cdc(engine, mode)
    position = f"{vlf:08X}:{offset:08X}:{slot:04X}"
    if mode == "cdc":
        task_config(payload)["cdc_start_position"] = position
    tree = generate(payload)
    task = next(v for v in tree.values() if 'resource "aws_dms_replication_task"' in v)
    assert (
        'contains(["sqlserver-ee", "sqlserver-se"], var.dms_database_origin-database_engine)'
        in task
    )
    assert "aws_dms_replication_instance.source-resource.engine_version" in task
    assert "can(regex(" in task
    assert "DMS 3.5.3 or newer" in task
    assert "start_replication_task = false" in task
    if mode == "cdc":
        assert f'cdc_start_position = "{position}"' in task
        assert "FullLoadSettings" not in task
    else:
        assert "cdc_start_position" not in task
        assert 'TargetTablePrepMode = "DO_NOTHING"' in task
    assert "archive" in task and "copy_" in task
    endpoint = next(v for v in tree.values() if 'endpoint_type = "source"' in v)
    assert 'ssl_mode = "verify-full"' in endpoint
    assert "password =" not in endpoint
    assert "secrets_manager_arn" in endpoint
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "version", [None, "3.4.7", "3.5.2", "3.5.2.9", "3.5", "3.5.3oops", "4."]
)
@pytest.mark.parametrize("mode", ["cdc", "full-load-and-cdc"])
def test_sqlserver_cdc_rejects_missing_old_or_malformed_dms_versions(version, mode):
    with pytest.raises(InvalidConnectionConfigError, match="3.5.3 or newer"):
        generate(sqlserver_cdc(mode=mode, version=version))


@pytest.mark.parametrize(
    "version", ["3.5.3", "3.5.3.1", "3.5.10", "3.6.0", "3.10.0", "4.0.0", "10.0.0"]
)
def test_sqlserver_cdc_accepts_numeric_newer_dms_versions(version):
    assert generate(sqlserver_cdc(version=version))


@pytest.mark.parametrize(
    "position",
    [
        "0000001:00000061:0001",
        "000000014:00000061:0001",
        "00000014:00000061:001",
        "00000014:00000061:00001",
        "00000014:0000006G:0001",
        "00000014:00000061:0001\n",
        "checkpoint:V1#1",
    ],
)
def test_invalid_sqlserver_lsns_rejected(position):
    config = task_config(sqlserver_cdc())
    config["cdc_start_position"] = position
    with pytest.raises(ValidationError):
        DmsReplicationTaskConfig.model_validate(config)


@pytest.mark.parametrize("position", ["mysql-bin.000001:4", "4AF/B00000D0"])
def test_sqlserver_cdc_rejects_other_native_position_formats(position):
    payload = sqlserver_cdc()
    task_config(payload)["cdc_start_position"] = position
    with pytest.raises(InvalidConnectionConfigError, match="native SQL Server LSN"):
        generate(payload)


@pytest.mark.parametrize("postgres", [False, True])
def test_other_engines_reject_sqlserver_lsns(postgres):
    payload = postgres_architecture() if postgres else cdc_architecture()
    task_config(payload)["cdc_start_position"] = "00000014:00000061:0001"
    with pytest.raises(InvalidConnectionConfigError, match="requires a native"):
        generate(payload)


def test_full_load_sqlserver_does_not_require_cdc_version():
    payload = sqlserver_migration("sqlserver-se", True)
    payload["resources"][0]["config"].pop("engine_version", None)
    tree = generate(payload)
    task = next(v for v in tree.values() if 'resource "aws_dms_replication_task"' in v)
    assert "3.5.3" not in task


def test_sqlserver_cdc_preview_exposes_external_setup():
    project = IRBuilder().build(ArchitectureDescription.model_validate(sqlserver_cdc()))
    message = ConnectionPreviewer().preview_all(project)[2].issues[0].message
    for prerequisite in (
        "MS-CDC",
        "every selected table",
        "backup access",
        "SQL Server LSN",
        "later apply can stop",
    ):
        assert prerequisite in message


@needs_terraform
@pytest.mark.parametrize("engine", EDITIONS)
@pytest.mark.parametrize("mode", ["cdc", "full-load-and-cdc"])
def test_sqlserver_cdc_projects_validate(engine, mode, tmp_path):
    validate_project(sqlserver_cdc(engine, mode), tmp_path)


@needs_terraform
def test_generated_version_guard_evaluates_in_terraform(tmp_path):
    tree = generate(sqlserver_cdc())
    task = next(v for v in tree.values() if 'resource "aws_dms_replication_task"' in v)
    condition = next(
        line.strip().removeprefix("condition = ")
        for line in task.splitlines()
        if "condition = can(regex(" in line
    )
    versions = [
        ("3.5.2", False),
        ("3.5.2.9", False),
        ("3.5.3", True),
        ("3.5.3.1", True),
        ("3.5.10", True),
        ("3.6.0", True),
        ("4.0.0", True),
        ("3.5.3oops", False),
    ]
    checks = [
        condition.replace(
            "aws_dms_replication_instance.source-resource.engine_version",
            json.dumps(version),
        )
        for version, _ in versions
    ]
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input="jsonencode([" + ", ".join(checks) + "])\n",
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(json.loads(result.stdout)) == [
        expected for _, expected in versions
    ]
