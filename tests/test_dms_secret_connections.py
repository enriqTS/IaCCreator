"""Secret endpoints compose with existing migrations without exposing credentials."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.dms import DmsSecretEndpointConfig
from tests.test_database_access_connections import generate
from tests.test_dms_database_connections import ENGINES, architecture
from tests.test_dms_replication_task_connections import (
    architecture as task_architecture,
)
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)


def secret_config():
    return architecture(kind="source_secret_endpoint")["connections"][0][
        "connection_config"
    ]


@given(engine=st.sampled_from(ENGINES), kind=st.sampled_from(["source", "target"]))
def test_secret_endpoint_uses_references_and_tls_without_iam_database_mutation(
    engine, kind
):
    target, database_engine, endpoint_engine, _ = engine
    payload = architecture(target, f"{kind}_secret_endpoint")
    payload["resources"][0]["config"].pop("engine_version", None)
    payload["resources"][1]["config"]["engine"] = database_engine
    tree = generate(payload)
    endpoint = next(v for v in tree.values() if 'resource "aws_dms_endpoint"' in v)
    assert f'engine_name = "{endpoint_engine}"' in endpoint
    assert f'endpoint_type = "{kind}"' in endpoint
    assert 'ssl_mode = "verify-ca"' in endpoint
    assert 'secrets_manager_arn = "arn:' in endpoint
    assert 'secrets_manager_access_role_arn = "arn:' in endpoint
    assert f'var.dms_database_target-resource_engine == "{database_engine}"' in endpoint
    assert "replication_instance_arn), 0, 5)" in endpoint
    for field in (
        "username =",
        "password =",
        "server_name =",
        "port =",
        "secret_string",
        "authentication_method",
    ):
        assert field not in endpoint
    text = "\n".join(tree.values())
    assert "iam_database_authentication_enabled = true" not in text
    assert 'resource "aws_iam_role_policy"' not in text
    assert "aws_secretsmanager_secret_version" not in text
    database_files = "\n".join(v for k, v in tree.items() if "/target-resource/" in k)
    assert "aws_dms_endpoint" not in database_files
    assert "module.source-resource" not in database_files


@pytest.mark.parametrize(
    "field,value",
    [
        ("secrets_manager_arn", "database"),
        (
            "secrets_manager_arn",
            "arn:aws:secretsmanager:us-east-1:123456789012:secret:*",
        ),
        ("secrets_manager_access_role_arn", "arn:aws:iam::123456789012:user/migration"),
        ("secrets_manager_access_role_arn", "arn:aws:iam::123456789012:role/*"),
        ("database_user", "migration"),
        ("password", "credentials"),
        ("endpoint_id", "invalid--id"),
    ],
)
def test_invalid_or_mixed_auth_configuration_rejected(field, value):
    config = secret_config()
    config[field] = value
    with pytest.raises(ValidationError):
        DmsSecretEndpointConfig.model_validate(config)


@pytest.mark.parametrize("reverse", [False, True])
def test_endpoint_ids_are_unique_across_authentication_methods(reverse):
    payload = architecture()
    other = deepcopy(payload["connections"][0])
    other["connection_type"] = "source_secret_endpoint"
    other["connection_config"] = secret_config()
    other["connection_config"]["endpoint_id"] = payload["connections"][0][
        "connection_config"
    ]["endpoint_id"].upper()
    payload["connections"].append(other)
    if reverse:
        payload["connections"].reverse()
    with pytest.raises(InvalidConnectionConfigError, match="unique"):
        generate(payload)


@pytest.mark.parametrize("engine", ["oracle-ee", "sqlserver-ex", "sqlserver-web"])
def test_unsupported_engines_rejected(engine):
    payload = architecture(kind="source_secret_endpoint")
    payload["resources"][1]["config"]["engine"] = engine
    with pytest.raises(InvalidConnectionConfigError, match="supported RDS/Aurora"):
        generate(payload)


def migration_payload(secret_source, secret_target, cdc=False):
    payload = task_architecture()
    for connection in payload["connections"]:
        if connection["connection_type"] in (
            {"source_endpoint"} if secret_source else set()
        ) | ({"target_endpoint"} if secret_target else set()):
            connection["connection_type"] = connection["connection_type"].replace(
                "_endpoint", "_secret_endpoint"
            )
            config = connection["connection_config"]
            config.pop("database_user")
            config.update(
                {
                    k: v
                    for k, v in secret_config().items()
                    if k.startswith("secrets_manager")
                }
            )
        elif cdc and connection["connection_type"] == "replication_task":
            connection["connection_config"]["migration_type"] = "full-load-and-cdc"
    if cdc:
        for resource in payload["resources"]:
            if resource["service_type"] == "rds":
                resource["config"]["engine"] = "mysql"
    return payload


@pytest.mark.parametrize(
    "secret_source,secret_target", [(True, False), (False, True), (True, True)]
)
@pytest.mark.parametrize("cdc", [False, True])
def test_tasks_accept_mixed_auth_and_deduplicate(secret_source, secret_target, cdc):
    payload = migration_payload(secret_source, secret_target, cdc)
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected
    assert sum('resource "aws_dms_endpoint"' in v for v in expected.values()) == 2
    assert any('resource "aws_dms_replication_task"' in v for v in expected.values())


@needs_terraform
@pytest.mark.parametrize(
    "secret_source,secret_target", [(True, False), (False, True), (True, True)]
)
def test_secret_migration_terraform_validates(secret_source, secret_target, tmp_path):
    _write_tree(tmp_path, generate(migration_payload(secret_source, secret_target)))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
