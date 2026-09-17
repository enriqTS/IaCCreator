"""SQL Server secret endpoints use hostname-verified TLS and bounded task modes."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ServiceType
from tests.test_database_access_connections import generate
from tests.test_dms_database_connections import architecture
from tests.test_dms_postgres_cdc import postgres_architecture
from tests.test_dms_replication_task_connections import task_config
from tests.test_dms_secret_connections import migration_payload, secret_config
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)

EDITIONS = ("sqlserver-ee", "sqlserver-se")


@given(engine=st.sampled_from(EDITIONS), kind=st.sampled_from(["source", "target"]))
def test_sqlserver_endpoints_use_secret_references_and_verified_hostname(engine, kind):
    payload = architecture(kind=f"{kind}_secret_endpoint")
    payload["resources"][1]["config"]["engine"] = engine
    tree = generate(payload)
    endpoint = next(v for v in tree.values() if 'resource "aws_dms_endpoint"' in v)
    assert 'engine_name = "sqlserver"' in endpoint
    assert 'ssl_mode = "verify-full"' in endpoint
    assert f'endpoint_type = "{kind}"' in endpoint
    assert f'var.dms_database_target-resource_engine == "{engine}"' in endpoint
    assert 'secrets_manager_arn = "arn:' in endpoint
    assert 'secrets_manager_access_role_arn = "arn:' in endpoint
    assert "replication_instance_arn), 0, 5)" in endpoint
    for field in (
        "username =",
        "password =",
        "server_name =",
        "port =",
        "mysql_settings",
        "postgres_settings",
    ):
        assert field not in endpoint
    text = "\n".join(tree.values())
    assert "iam_database_authentication_enabled = true" not in text
    assert "aws_secretsmanager_secret_version" not in text
    database_files = "\n".join(v for k, v in tree.items() if "/target-resource/" in k)
    assert "aws_dms_endpoint" not in database_files
    assert "module.source-resource" not in database_files
    payload["connections"] *= 2
    assert generate(payload) == tree


@pytest.mark.parametrize("engine", EDITIONS)
@pytest.mark.parametrize("kind", ["source_endpoint", "target_endpoint"])
def test_sqlserver_does_not_gain_iam_authentication_support(engine, kind):
    payload = architecture(kind=kind)
    payload["resources"][1]["config"]["engine"] = engine
    with pytest.raises(InvalidConnectionConfigError, match="DMS IAM endpoints require"):
        generate(payload)


@pytest.mark.parametrize("engine", EDITIONS)
def test_sqlserver_is_not_an_aurora_engine(engine):
    payload = architecture(ServiceType.AURORA, "source_secret_endpoint")
    payload["resources"][1]["config"]["engine"] = engine
    with pytest.raises(
        InvalidConnectionConfigError, match="DMS secret endpoints require"
    ):
        generate(payload)


def test_postgres_source_settings_are_rejected_on_sqlserver():
    payload = architecture(kind="source_secret_endpoint")
    payload["resources"][1]["config"]["engine"] = "sqlserver-se"
    payload["connections"][0]["connection_config"]["postgres_plugin_name"] = "pglogical"
    with pytest.raises(InvalidConnectionConfigError, match="PostgreSQL source"):
        generate(payload)


def sqlserver_migration(engine, source):
    payload = migration_payload(True, True)
    payload["resources"][2 if source else 1]["config"]["engine"] = engine
    task_config(payload)["table_schema"] = "dbo" if source else "public"
    task_config(payload).update(target_schema="archive", target_table_prefix="copy_")
    return payload


def sqlserver_cdc_target(engine, postgres):
    payload = (
        postgres_architecture() if postgres else migration_payload(True, True, cdc=True)
    )
    payload["resources"][1]["config"]["engine"] = engine
    endpoint = payload["connections"][0]
    endpoint["connection_type"] = "target_secret_endpoint"
    endpoint["connection_config"].pop("database_user", None)
    endpoint["connection_config"].update(
        {k: v for k, v in secret_config().items() if k.startswith("secrets_manager")}
    )
    return payload


@needs_terraform
@pytest.mark.parametrize("engine", EDITIONS)
@pytest.mark.parametrize("source", [False, True])
def test_sqlserver_full_load_projects_validate(engine, source, tmp_path):
    validate_project(sqlserver_migration(engine, source), tmp_path)


@needs_terraform
@pytest.mark.parametrize("engine", EDITIONS)
@pytest.mark.parametrize("postgres", [False, True])
def test_sqlserver_targets_accept_supported_source_cdc(engine, postgres, tmp_path):
    validate_project(sqlserver_cdc_target(engine, postgres), tmp_path)


def validate_project(payload, tmp_path):
    tree = generate(payload)
    task = next(v for v in tree.values() if 'resource "aws_dms_replication_task"' in v)
    assert "start_replication_task = false" in task
    assert "source_endpoint_arn = aws_dms_endpoint." in task
    assert "target_endpoint_arn = aws_dms_endpoint." in task
    _write_tree(tmp_path, tree)
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
