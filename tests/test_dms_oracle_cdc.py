"""Non-CDB Oracle CDC uses LogMiner and native decimal SCNs."""

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
from tests.test_dms_oracle_connections import oracle_migration
from tests.test_dms_postgres_cdc import postgres_architecture
from tests.test_dms_replication_task_connections import task_config
from tests.test_dms_sqlserver_cdc import sqlserver_cdc
from tests.test_dms_sqlserver_connections import validate_project
from tests.test_generated_project_validates import needs_terraform


def oracle_cdc(engine="oracle-se2", mode="cdc"):
    payload = oracle_migration(engine, True)
    task_config(payload)["migration_type"] = mode
    if mode == "cdc":
        task_config(payload)["cdc_start_position"] = "123456789"
    return payload


@given(
    engine=st.sampled_from(["oracle-ee", "oracle-se2"]),
    mode=st.sampled_from(["cdc", "full-load-and-cdc"]),
    scn=st.integers(min_value=1, max_value=2**64 - 1),
)
def test_oracle_cdc_preserves_scn_and_guards_source(engine, mode, scn):
    payload = oracle_cdc(engine, mode)
    if mode == "cdc":
        task_config(payload)["cdc_start_position"] = str(scn)
    tree = generate(payload)
    task = next(v for v in tree.values() if 'resource "aws_dms_replication_task"' in v)
    assert (
        'contains(["oracle-ee", "oracle-se2"], var.dms_database_origin-database_engine)'
        in task
    )
    assert "start_replication_task = false" in task
    assert "ARCHIVE" in task and "COPY_" in task
    if mode == "cdc":
        assert f'cdc_start_position = "{scn}"' in task
        assert "FullLoadSettings" not in task
    else:
        assert "cdc_start_position" not in task
        assert 'TargetTablePrepMode = "DO_NOTHING"' in task
    endpoint = next(v for v in tree.values() if 'endpoint_type = "source"' in v)
    assert 'engine_name = "oracle"' in endpoint
    assert 'ssl_mode = "verify-ca"' in endpoint
    assert "secrets_manager_arn" in endpoint
    assert "password =" not in endpoint
    assert "oracle_settings" not in endpoint
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "position", ["0", "01", "-1", "+1", "1.5", "1e6", "１２３", "123\n"]
)
def test_oracle_scn_rejects_noncanonical_decimal(position):
    config = task_config(oracle_cdc())
    config["cdc_start_position"] = position
    with pytest.raises(ValidationError):
        DmsReplicationTaskConfig.model_validate(config)


@pytest.mark.parametrize(
    "position", ["mysql-bin.000001:4", "4AF/B00000D0", "00000014:00000061:0001"]
)
def test_oracle_rejects_other_engine_positions(position):
    payload = oracle_cdc()
    task_config(payload)["cdc_start_position"] = position
    with pytest.raises(InvalidConnectionConfigError, match="native Oracle SCN"):
        generate(payload)


@pytest.mark.parametrize(
    "factory", [cdc_architecture, postgres_architecture, sqlserver_cdc]
)
def test_other_sources_reject_oracle_scn(factory):
    payload = factory()
    task_config(payload)["cdc_start_position"] = "123456789"
    with pytest.raises(InvalidConnectionConfigError, match="requires a native"):
        generate(payload)


def test_oracle_cdc_preview_exposes_prerequisites():
    project = IRBuilder().build(ArchitectureDescription.model_validate(oracle_cdc()))
    message = ConnectionPreviewer().preview_all(project)[2].issues[0].message
    for text in (
        "LogMiner",
        "supplemental logging",
        "archive logs",
        "earliest open transaction",
        "Oracle SCN",
        "later apply can stop",
    ):
        assert text in message


@needs_terraform
@pytest.mark.parametrize("engine", ["oracle-ee", "oracle-se2"])
@pytest.mark.parametrize("mode", ["cdc", "full-load-and-cdc"])
def test_oracle_cdc_projects_validate(engine, mode, tmp_path):
    validate_project(oracle_cdc(engine, mode), tmp_path)
