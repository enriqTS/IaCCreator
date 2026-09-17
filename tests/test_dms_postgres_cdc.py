"""PostgreSQL CDC preserves native WAL positions and exclusive slot ownership."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.dms_source import DmsSecretSourceEndpointConfig
from app.models.connection_configs.dms_task import DmsReplicationTaskConfig
from app.models.input_models import ServiceType
from tests.test_database_access_connections import generate
from tests.test_dms_cdc_tasks import cdc_architecture
from tests.test_dms_replication_task_connections import task_config
from tests.test_dms_secret_connections import secret_config
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)

SOURCES = [(ServiceType.RDS, "postgres"), (ServiceType.AURORA, "aurora-postgresql")]


def postgres_architecture(
    source=ServiceType.RDS, engine="postgres", mode="cdc", plugin="test-decoding"
):
    payload = cdc_architecture(source, engine, mode)
    endpoint = payload["connections"][1]
    endpoint["connection_type"] = "source_secret_endpoint"
    config = endpoint["connection_config"]
    config.pop("database_user")
    config.update(
        {
            key: value
            for key, value in secret_config().items()
            if key.startswith("secrets_manager")
        }
    )
    config["postgres_plugin_name"] = plugin
    if mode == "cdc":
        config["postgres_slot_name"] = "migration_slot"
        task_config(payload)["cdc_start_position"] = "4AF/B00000D0"
    return payload


@given(
    source=st.sampled_from(SOURCES),
    mode=st.sampled_from(["cdc", "full-load-and-cdc"]),
    plugin=st.sampled_from(["test-decoding", "pglogical"]),
    high=st.integers(min_value=0, max_value=2**32 - 1),
    low=st.integers(min_value=1, max_value=2**32 - 1),
)
def test_postgres_tasks_preserve_lsn_plugin_and_engine_guard(
    source, mode, plugin, high, low
):
    payload = postgres_architecture(*source, mode, plugin)
    if mode == "cdc":
        task_config(payload)["cdc_start_position"] = f"{high:X}/{low:X}"
    tree = generate(payload)
    task = next(v for v in tree.values() if 'resource "aws_dms_replication_task"' in v)
    endpoint = next(v for v in tree.values() if 'endpoint_type = "source"' in v)
    assert f'plugin_name = "{plugin}"' in endpoint
    assert "postgres_settings {" in endpoint
    assert "capture_ddls = true" in endpoint
    assert (
        'contains(["postgres", "aurora-postgresql"], var.dms_database_origin-database_engine)'
        in task
    )
    assert "start_replication_task = false" in task
    assert "password =" not in endpoint
    if mode == "cdc":
        assert f'cdc_start_position = "{high:X}/{low:X}"' in task
        assert 'slot_name = "migration_slot"' in endpoint
        assert "FullLoadSettings" not in task
    else:
        assert "cdc_start_position" not in task
        assert "slot_name" not in endpoint
        assert 'TargetTablePrepMode = "DO_NOTHING"' in task
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


def test_full_load_and_cdc_can_use_dms_default_plugin_and_slot_creation():
    payload = postgres_architecture(mode="full-load-and-cdc")
    payload["connections"][1]["connection_config"].pop("postgres_plugin_name")
    assert generate(payload)


@pytest.mark.parametrize(
    "value",
    ["FFFFFFFFF/1", "1/FFFFFFFFF", "G/1", "1/", "1/2\n", "checkpoint:V1#1", "1/-1"],
)
def test_invalid_lsn_rejected(value):
    config = task_config(postgres_architecture())
    config["cdc_start_position"] = value
    with pytest.raises(ValidationError):
        DmsReplicationTaskConfig.model_validate(config)


@pytest.mark.parametrize(
    "slot", ["UPPER", "has-hyphen", "slot/name", "a" * 64, "name\n"]
)
def test_invalid_slot_rejected(slot):
    config = postgres_architecture()["connections"][1]["connection_config"]
    config["postgres_slot_name"] = slot
    with pytest.raises(ValidationError):
        DmsSecretSourceEndpointConfig.model_validate(config)


def test_slot_requires_explicit_matching_plugin():
    config = postgres_architecture()["connections"][1]["connection_config"]
    config.pop("postgres_plugin_name")
    with pytest.raises(ValidationError, match="decoding plugin"):
        DmsSecretSourceEndpointConfig.model_validate(config)


def test_postgres_cdc_only_requires_slot():
    payload = postgres_architecture()
    payload["connections"][1]["connection_config"].pop("postgres_slot_name")
    with pytest.raises(
        InvalidConnectionConfigError, match="existing logical replication slot"
    ):
        generate(payload)


def test_full_load_and_cdc_uses_dms_managed_slot():
    payload = postgres_architecture(mode="full-load-and-cdc")
    payload["connections"][1]["connection_config"]["postgres_slot_name"] = "old_slot"
    with pytest.raises(InvalidConnectionConfigError, match="only for CDC-only"):
        generate(payload)


@pytest.mark.parametrize("postgres", [False, True])
def test_native_positions_must_match_source_engine(postgres):
    payload = postgres_architecture() if postgres else cdc_architecture()
    task_config(payload)["cdc_start_position"] = (
        "mysql-bin.000001:4" if postgres else "4AF/B00000D0"
    )
    with pytest.raises(InvalidConnectionConfigError, match="native"):
        generate(payload)


@pytest.mark.parametrize("field", ["postgres_slot_name", "postgres_plugin_name"])
def test_postgres_settings_rejected_on_mysql_source(field):
    payload = postgres_architecture()
    payload["resources"][2]["config"]["engine"] = "mysql"
    if field == "postgres_plugin_name":
        payload["connections"][1]["connection_config"].pop("postgres_slot_name")
    with pytest.raises(
        InvalidConnectionConfigError, match="PostgreSQL.*require a PostgreSQL source"
    ):
        generate(payload)


def test_postgres_settings_rejected_on_target_endpoint():
    payload = postgres_architecture()
    payload["connections"][1]["connection_type"] = "target_secret_endpoint"
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize("separate_endpoint", [False, True])
def test_named_slot_cannot_be_shared_by_distinct_tasks(separate_endpoint):
    payload = postgres_architecture()
    task = deepcopy(payload["connections"][2])
    task["connection_config"]["task_id"] = "another-task"
    if separate_endpoint:
        endpoint = deepcopy(payload["connections"][1])
        endpoint["connection_config"]["endpoint_id"] = "another-source"
        task["connection_config"]["source_endpoint_id"] = "another-source"
        payload["connections"].append(endpoint)
    payload["connections"].append(task)
    with pytest.raises(InvalidConnectionConfigError, match="cannot be shared"):
        generate(payload)


def test_distinct_slots_allow_multiple_cdc_tasks():
    payload = postgres_architecture()
    endpoint = deepcopy(payload["connections"][1])
    endpoint["connection_config"].update(
        endpoint_id="other-source", postgres_slot_name="other_slot"
    )
    task = deepcopy(payload["connections"][2])
    task["connection_config"].update(
        task_id="other-task", source_endpoint_id="other-source"
    )
    payload["connections"].extend([endpoint, task])
    assert generate(payload)


@needs_terraform
@pytest.mark.parametrize("source,engine", SOURCES)
@pytest.mark.parametrize("mode", ["cdc", "full-load-and-cdc"])
@pytest.mark.parametrize("plugin", ["test-decoding", "pglogical"])
def test_postgres_cdc_terraform_validates(source, engine, mode, plugin, tmp_path):
    payload = postgres_architecture(source, engine, mode, plugin)
    task_config(payload).update(target_schema="archive", target_table_prefix="copy_")
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
