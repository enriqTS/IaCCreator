"""Oracle endpoints preserve wallet references and full-load source boundaries."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.connection_previewer import ConnectionPreviewer
from app.services.ir_builder import IRBuilder
from tests.test_database_access_connections import generate
from tests.test_dms_database_connections import architecture
from tests.test_dms_postgres_cdc import postgres_architecture
from tests.test_dms_replication_task_connections import task_config
from tests.test_dms_secret_connections import migration_payload, secret_config
from tests.test_dms_sqlserver_cdc import sqlserver_cdc
from tests.test_dms_sqlserver_connections import validate_project
from tests.test_generated_project_validates import needs_terraform

ENGINES = ("oracle-ee", "oracle-se2", "oracle-ee-cdb", "oracle-se2-cdb")


@given(engine=st.sampled_from(ENGINES), kind=st.sampled_from(["source", "target"]))
def test_oracle_endpoint_uses_secret_and_imported_wallet(engine, kind):
    payload = architecture(kind=f"{kind}_secret_endpoint")
    payload["resources"][1]["config"]["engine"] = engine
    config = payload["connections"][0]["connection_config"]
    config["database_name"] = "ORCLPDB1" if engine.endswith("-cdb") else "ORCL"
    config["certificate_arn"] = "arn:aws:dms:us-east-1:123456789012:cert:oracle-wallet"
    tree = generate(payload)
    endpoint = next(v for v in tree.values() if 'resource "aws_dms_endpoint"' in v)
    assert 'engine_name = "oracle"' in endpoint
    assert 'ssl_mode = "verify-ca"' in endpoint
    assert f'endpoint_type = "{kind}"' in endpoint
    assert f'database_name = "{config["database_name"]}"' in endpoint
    assert config["certificate_arn"] in endpoint
    assert f'var.dms_database_target-resource_engine == "{engine}"' in endpoint
    assert 'secrets_manager_arn = "arn:' in endpoint
    assert 'secrets_manager_access_role_arn = "arn:' in endpoint
    assert "replication_instance_arn), 0, 5)" in endpoint
    for field in (
        "username =",
        "password =",
        "server_name =",
        "port =",
        "postgres_settings",
        "mysql_settings",
        "oracle_settings",
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


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("kind", ["source_endpoint", "target_endpoint"])
def test_oracle_iam_endpoints_remain_rejected(engine, kind):
    payload = architecture(kind=kind)
    payload["resources"][1]["config"]["engine"] = engine
    with pytest.raises(InvalidConnectionConfigError, match="DMS IAM endpoints require"):
        generate(payload)


@pytest.mark.parametrize("engine", ENGINES)
def test_oracle_engines_are_not_accepted_on_aurora(engine):
    payload = architecture(ServiceType.AURORA, "source_secret_endpoint")
    payload["resources"][1]["config"]["engine"] = engine
    with pytest.raises(
        InvalidConnectionConfigError, match="DMS secret endpoints require"
    ):
        generate(payload)


def oracle_migration(engine, source):
    payload = migration_payload(True, True)
    payload["resources"][2 if source else 1]["config"]["engine"] = engine
    endpoint = payload["connections"][1 if source else 0]
    endpoint["connection_config"]["database_name"] = (
        "ORCLPDB1" if engine.endswith("-cdb") else "ORCL"
    )
    task_config(payload).update(
        table_schema="APP",
        table_names="CUSTOMERS,ORDERS",
        target_schema="ARCHIVE",
        target_table_prefix="COPY_",
    )
    return payload


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("mode", ["cdc", "full-load-and-cdc"])
def test_oracle_source_cdc_remains_rejected(engine, mode):
    payload = oracle_migration(engine, True)
    task_config(payload)["migration_type"] = mode
    if mode == "cdc":
        task_config(payload)["cdc_start_position"] = "mysql-bin.000001:4"
    with pytest.raises(InvalidConnectionConfigError, match="CDC sources must use"):
        generate(payload)


def test_oracle_rejects_postgres_source_options():
    payload = architecture(kind="source_secret_endpoint")
    payload["resources"][1]["config"]["engine"] = "oracle-se2"
    payload["connections"][0]["connection_config"]["postgres_plugin_name"] = "pglogical"
    with pytest.raises(InvalidConnectionConfigError, match="PostgreSQL source"):
        generate(payload)


def test_oracle_preview_explains_wallet_and_service_prerequisites():
    project = IRBuilder().build(
        ArchitectureDescription.model_validate(oracle_migration("oracle-ee-cdb", True))
    )
    messages = " ".join(
        issue.message for issue in ConnectionPreviewer().preview_all(project)[1].issues
    )
    for text in (
        "auto-login wallet",
        "TLS listener port",
        "service or PDB",
        "Oracle-source CDC is not implemented",
    ):
        assert text in messages


@needs_terraform
@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("source", [False, True])
def test_oracle_full_load_tasks_validate(engine, source, tmp_path):
    payload = oracle_migration(engine, source)
    tree = generate(payload)
    task = next(v for v in tree.values() if 'resource "aws_dms_replication_task"' in v)
    for name in ("APP", "CUSTOMERS", "ORDERS", "ARCHIVE", "COPY_"):
        assert name in task
    validate_project(payload, tmp_path)


@needs_terraform
@pytest.mark.parametrize("family", ["mysql", "postgres", "sqlserver"])
def test_oracle_targets_accept_supported_source_cdc(family, tmp_path):
    payload = (
        postgres_architecture()
        if family == "postgres"
        else sqlserver_cdc()
        if family == "sqlserver"
        else migration_payload(True, True, cdc=True)
    )
    payload["resources"][1]["config"]["engine"] = "oracle-se2-cdb"
    endpoint = payload["connections"][0]
    endpoint["connection_type"] = "target_secret_endpoint"
    endpoint["connection_config"].pop("database_user", None)
    endpoint["connection_config"].update(
        {k: v for k, v in secret_config().items() if k.startswith("secrets_manager")}
    )
    endpoint["connection_config"]["database_name"] = "ORCLPDB1"
    validate_project(payload, tmp_path)
