"""DMS endpoints preserve database identity, credentials, and module ownership."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.dms import DmsIamEndpointConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from tests.generator_helpers import connection_architecture
from tests.test_database_access_connections import generate
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)

ENGINES = [
    (ServiceType.RDS, "mysql", "mysql", "mysql_settings"),
    (ServiceType.RDS, "mariadb", "mariadb", "mysql_settings"),
    (ServiceType.RDS, "postgres", "postgres", "postgres_settings"),
    (ServiceType.AURORA, "aurora-mysql", "aurora", "mysql_settings"),
    (ServiceType.AURORA, "aurora-postgresql", "aurora-postgresql", "postgres_settings"),
]


def architecture(target=ServiceType.RDS, kind="source_endpoint"):
    return connection_architecture(
        resolve_spec(ServiceType.DATABASE_MIGRATION_SERVICE, target, kind, {})
    )


@given(
    engine=st.sampled_from(ENGINES),
    kind=st.sampled_from(["source_endpoint", "target_endpoint"]),
    username=st.from_regex(r"[a-z][a-z0-9_]{0,15}", fullmatch=True),
)
def test_endpoint_uses_native_database_identity_and_scoped_role(engine, kind, username):
    target, database_engine, endpoint_engine, settings = engine
    payload = architecture(target, kind)
    payload["resources"][1]["config"]["engine"] = database_engine
    payload["connections"][0]["connection_config"]["database_user"] = username
    tree = generate(payload)
    text = "\n".join(tree.values())
    endpoint = next(
        v
        for k, v in tree.items()
        if k.endswith(".tf") and 'resource "aws_dms_endpoint"' in v
    )
    assert f'endpoint_type = "{kind.removesuffix("_endpoint")}"' in endpoint
    assert f'engine_name = "{endpoint_engine}"' in endpoint
    assert f"{settings} {{" in endpoint
    assert 'authentication_method = "iam"' in endpoint
    assert 'ssl_mode = "verify-ca"' in endpoint
    assert "server_name = var.dms_database_target-resource_host" in endpoint
    assert "port = tonumber(var.dms_database_target-resource_port)" in endpoint
    assert (
        f'format("%s/{username}", var.dms_database_target-resource_iam_resource_arn)'
        in endpoint
    )
    assert "rds-db:connect" in endpoint
    assert "depends_on = [aws_iam_role_policy." in endpoint
    assert f'var.dms_database_target-resource_engine == "{database_engine}"' in endpoint
    assert "replication_instance_arn), 0, 5)" in endpoint
    assert "iam_database_authentication_enabled = true" in text
    assert ":rds-db:%s:%s:dbuser:%s" in text
    assert "can(regex(" in text and "self.engine_version" in text
    assert "module.target-resource.iam_database_host" in text
    assert "password =" not in endpoint
    assert "secretsmanager:GetSecretValue" not in text
    assert "secret_string" not in text
    assert "aws_dms_replication_task" not in text
    database_files = "\n".join(v for k, v in tree.items() if "/target-resource/" in k)
    assert "iam_database_host" in database_files
    assert "aws_dms_endpoint" not in database_files
    assert "module.source-resource" not in database_files


@pytest.mark.parametrize(
    "version", [None, "3.5.4", "3.6.0", "3.6.0.9", "3.7.invalid", "4.", "3.6.1oops"]
)
def test_unsupported_or_unspecified_replication_version_is_rejected(version):
    payload = architecture()
    payload["resources"][0]["config"]["engine_version"] = version
    with pytest.raises(InvalidConnectionConfigError, match="3.6.1"):
        generate(payload)


@pytest.mark.parametrize("version", ["3.6.1", "3.6.10", "3.6.1.2", "3.7.0", "4.0.0"])
def test_minimum_version_guard_accepts_newer_numeric_versions(version):
    payload = architecture()
    payload["resources"][0]["config"]["engine_version"] = version
    assert generate(payload)


@pytest.mark.parametrize("engine", ["oracle-ee", "sqlserver-se", None])
def test_unsupported_database_engine_is_rejected(engine):
    payload = architecture()
    payload["resources"][1]["config"]["engine"] = engine
    with pytest.raises(InvalidConnectionConfigError, match="supported RDS/Aurora"):
        generate(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("endpoint_id", "invalid--name"),
        ("endpoint_id", "invalid-"),
        ("endpoint_id", "1invalid"),
        ("endpoint_id", "invalid_name"),
        ("database_user", "*"),
        ("database_user", "user/*"),
        ("database_name", "${database}"),
        ("database_name", ""),
        ("certificate_arn", "arn:aws:acm:us-east-1:123456789012:certificate/abc"),
        ("certificate_arn", "arn:aws:dms:us-east-1:123456789012:cert:*"),
    ],
)
def test_invalid_endpoint_configuration_is_rejected(field, value):
    config = architecture()["connections"][0]["connection_config"]
    config[field] = value
    with pytest.raises(ValidationError):
        DmsIamEndpointConfig.model_validate(config)


def test_identifiers_are_normalized_before_conflict_detection():
    payload = architecture()
    duplicate = deepcopy(payload["connections"][0])
    duplicate["connection_config"]["endpoint_id"] = duplicate["connection_config"][
        "endpoint_id"
    ].upper()
    expected = generate(payload)
    payload["connections"].append(duplicate)
    assert generate(payload) == expected
    duplicate["connection_config"]["database_user"] = "other_user"
    with pytest.raises(InvalidConnectionConfigError, match="unique"):
        generate(payload)


@pytest.mark.parametrize("change", ["kind", "user", "database", "source"])
def test_project_wide_endpoint_id_conflicts_are_rejected(change):
    payload = architecture()
    duplicate = deepcopy(payload["connections"][0])
    if change == "kind":
        duplicate["connection_type"] = "target_endpoint"
    elif change == "user":
        duplicate["connection_config"]["database_user"] = "other_user"
    else:
        index, field = (1, "target") if change == "database" else (0, "source")
        resource = deepcopy(payload["resources"][index])
        resource["id"] = "another"
        resource["name"] = "another"
        payload["resources"].append(resource)
        duplicate[field] = "another"
        duplicate[f"{field}_id"] = "another"
    payload["connections"].append(duplicate)
    with pytest.raises(InvalidConnectionConfigError, match="unique"):
        generate(payload)


def paired_endpoints(target, engine):
    payload = architecture(target)
    payload["resources"][1]["config"]["engine"] = engine
    second = deepcopy(payload["connections"][0])
    second["connection_type"] = "target_endpoint"
    second["connection_config"].update(
        endpoint_id="app-destination", database_user="destination_user"
    )
    payload["connections"].append(second)
    return payload


def test_multiple_endpoints_are_deterministic_and_share_native_outputs():
    payload = paired_endpoints(ServiceType.RDS, "postgres")
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected
    text = "\n".join(expected.values())
    assert text.count('resource "aws_dms_endpoint"') == 2
    assert text.count('data "aws_partition" "dms_endpoints"') == 1
    assert text.count('resource "aws_iam_role_policy" "endpoint_') == 2


@needs_terraform
@pytest.mark.parametrize("target,engine,endpoint_engine,settings", ENGINES)
def test_source_and_target_endpoints_validate_without_dependency_cycles(
    target, engine, endpoint_engine, settings, tmp_path
):
    _write_tree(tmp_path, generate(paired_endpoints(target, engine)))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
