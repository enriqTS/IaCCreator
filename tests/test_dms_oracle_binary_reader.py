"""Oracle Binary Reader settings stay typed and restricted to source endpoints."""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.dms import DmsSecretEndpointConfig
from app.models.connection_configs.dms_source import DmsSecretSourceEndpointConfig
from tests.test_database_access_connections import generate
from tests.test_dms_oracle_cdc import oracle_cdc
from tests.test_dms_oracle_connections import ENGINES, oracle_migration
from tests.test_dms_replication_task_connections import task_config
from tests.test_dms_sqlserver_connections import validate_project
from tests.test_generated_project_validates import needs_terraform


def binary_reader(engine="oracle-se2-cdb", mode="cdc"):
    payload = oracle_cdc(engine, mode)
    payload["connections"][1]["connection_config"]["oracle_cdc_reader"] = (
        "binary-reader"
    )
    return payload


@given(
    engine=st.sampled_from(ENGINES),
    mode=st.sampled_from(["cdc", "full-load-and-cdc"]),
    scn=st.integers(min_value=1, max_value=2**64 - 1),
)
def test_binary_reader_preserves_native_scn_and_source_guards(engine, mode, scn):
    payload = binary_reader(engine, mode)
    if mode == "cdc":
        task_config(payload)["cdc_start_position"] = str(scn)
    tree = generate(payload)
    endpoint = next(v for v in tree.values() if 'endpoint_type = "source"' in v)
    assert 'extra_connection_attributes = "useLogminerReader=N;useBfile=Y;"' in endpoint
    assert 'ssl_mode = "verify-ca"' in endpoint
    assert "secrets_manager_arn" in endpoint
    assert "password =" not in endpoint
    task = next(v for v in tree.values() if 'resource "aws_dms_replication_task"' in v)
    engines = (
        '["oracle-ee-cdb", "oracle-se2-cdb"]'
        if engine.endswith("-cdb")
        else '["oracle-ee", "oracle-se2"]'
    )
    assert f"contains({engines}, var.dms_database_origin-database_engine)" in task
    assert "start_replication_task = false" in task
    if mode == "cdc":
        assert f'cdc_start_position = "{scn}"' in task
    else:
        assert "cdc_start_position" not in task
    target = next(v for v in tree.values() if 'endpoint_type = "target"' in v)
    assert "extra_connection_attributes" not in target
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


@pytest.mark.parametrize("engine", ["mysql", "postgres", "sqlserver-se"])
@pytest.mark.parametrize("reader", ["logminer", "binary-reader"])
def test_reader_rejected_on_non_oracle_sources(engine, reader):
    payload = oracle_migration(engine, True)
    payload["connections"][1]["connection_config"]["oracle_cdc_reader"] = reader
    with pytest.raises(InvalidConnectionConfigError, match="require an Oracle source"):
        generate(payload)


@pytest.mark.parametrize("reader", [None, "logminer"])
@pytest.mark.parametrize("engine", ["oracle-ee-cdb", "oracle-se2-cdb"])
@pytest.mark.parametrize("mode", ["cdc", "full-load-and-cdc"])
def test_pdb_cdc_requires_binary_reader(engine, mode, reader):
    payload = oracle_cdc(engine, mode)
    payload["connections"][1]["connection_config"]["oracle_cdc_reader"] = reader
    with pytest.raises(InvalidConnectionConfigError, match="requires Binary Reader"):
        generate(payload)


@pytest.mark.parametrize("reader", ["logminer", "binary-reader"])
def test_target_rejects_reader_options(reader):
    config = binary_reader()["connections"][1]["connection_config"]
    config["oracle_cdc_reader"] = reader
    with pytest.raises(ValidationError, match="Extra inputs"):
        DmsSecretEndpointConfig.model_validate(config)


@pytest.mark.parametrize("reader", ["binary", "useBfile=Y", True])
def test_reader_rejects_untyped_options(reader):
    config = binary_reader()["connections"][1]["connection_config"]
    config["oracle_cdc_reader"] = reader
    with pytest.raises(ValidationError):
        DmsSecretSourceEndpointConfig.model_validate(config)


def test_reader_schema_and_blank_default():
    fields = DmsSecretSourceEndpointConfig.get_field_schema()
    field = next(field for field in fields if field.key == "oracle_cdc_reader")
    assert {option.value for option in field.options} == {"logminer", "binary-reader"}
    config = binary_reader()["connections"][1]["connection_config"]
    config["oracle_cdc_reader"] = ""
    assert (
        DmsSecretSourceEndpointConfig.model_validate(config).oracle_cdc_reader is None
    )


def test_explicit_logminer_disables_binary_reader():
    payload = oracle_cdc()
    payload["connections"][1]["connection_config"]["oracle_cdc_reader"] = "logminer"
    assert any(
        'extra_connection_attributes = "useLogminerReader=Y;useBfile=N;"' in v
        for v in generate(payload).values()
    )


@pytest.mark.parametrize("field", ["table_schema", "table_names"])
@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("mode", ["cdc", "full-load-and-cdc"])
def test_oracle_cdc_identifier_limit(engine, mode, field):
    payload = binary_reader(engine, mode)
    task_config(payload)[field] = "A" * 30
    assert generate(payload)
    task_config(payload)[field] = "A" * 31
    with pytest.raises(InvalidConnectionConfigError, match="must not exceed 30 bytes"):
        generate(payload)
    task_config(payload)["migration_type"] = "full-load"
    task_config(payload).pop("cdc_start_position", None)
    assert generate(payload)


@needs_terraform
@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("mode", ["cdc", "full-load-and-cdc"])
def test_binary_reader_projects_validate(engine, mode, tmp_path):
    validate_project(binary_reader(engine, mode), tmp_path)
