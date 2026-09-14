"""Database IAM access preserves SQL and credential ownership."""

import json
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.database import DatabaseIamAuthConfig
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)


def architecture(source=ServiceType.LAMBDA, target=ServiceType.RDS):
    return connection_architecture(resolve_spec(source, target, "authenticates_to", {}))


def generate(payload):
    return CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))
    )


@given(
    source=st.sampled_from([ServiceType.LAMBDA, ServiceType.ECS]),
    target=st.sampled_from([ServiceType.RDS, ServiceType.AURORA]),
    username=st.from_regex(r"[a-z][a-z0-9_]{0,15}", fullmatch=True),
)
def test_login_grants_are_scoped_to_resource_id_and_user(source, target, username):
    payload = architecture(source, target)
    payload["connections"][0]["connection_config"]["database_user"] = username
    tree = generate(payload)
    policy = json.loads(
        tree["connection-check/iam-policies/source-resource-policy.json"]
    )
    grants = [s for s in policy["Statement"] if "rds-db:connect" in s["Action"]]
    assert grants == [
        {
            "Effect": "Allow",
            "Action": ["rds-db:connect"],
            "Resource": "${var.database_target-resource_iam_resource_arn}/" + username,
        }
    ]
    text = "\n".join(tree.values())
    assert "iam_database_authentication_enabled = true" in text
    assert ":rds-db:%s:%s:dbuser:%s" in text
    resource = "aws_db_instance" if target == ServiceType.RDS else "aws_rds_cluster"
    attribute = "resource_id" if target == ServiceType.RDS else "cluster_resource_id"
    assert f"{resource}.target-resource.{attribute}" in text
    assert "module.target-resource.iam_database_host" in text
    assert "module.target-resource.iam_database_port" in text
    assert "module.target-resource.iam_database_region" in text
    assert "manage_master_user_password" not in text
    assert "secretsmanager:GetSecretValue" not in text
    assert "random_password" not in text
    assert "contains([" in text and "var.engine)" in text
    if source == ServiceType.ECS:
        assert "task_role_arn = aws_iam_role.source-resource_role.arn" in text


@pytest.mark.parametrize("username", ["*", "app/*", "a?", "", "a" * 33, "${admin}"])
def test_wildcard_and_invalid_users_are_rejected(username):
    with pytest.raises(ValidationError):
        DatabaseIamAuthConfig(database_user=username)


@pytest.mark.parametrize(
    "target,engine",
    [
        (ServiceType.RDS, "oracle-ee"),
        (ServiceType.RDS, None),
        (ServiceType.AURORA, "mysql"),
    ],
)
def test_unsupported_database_engines_are_rejected(target, engine):
    payload = architecture(target=target)
    payload["resources"][1]["config"]["engine"] = engine
    with pytest.raises(InvalidConnectionConfigError, match="supported database engine"):
        generate(payload)


@pytest.mark.parametrize("target", [ServiceType.RDS, ServiceType.AURORA])
def test_master_password_management_requires_explicit_opt_in(target):
    payload = architecture(target=target)
    config = payload["resources"][1]["config"]
    config["manage_master_user_password"] = True
    config["username" if target == ServiceType.RDS else "master_username"] = (
        "administrator"
    )
    text = "\n".join(generate(payload).values())
    assert "manage_master_user_password = var.manage_master_user_password" in text
    assert "secret_string" not in text
    payload["connections"] = []
    text = "\n".join(generate(payload).values())
    assert "iam_database_authentication_enabled" not in text
    assert "manage_master_user_password = var.manage_master_user_password" in text


@pytest.mark.parametrize("target", [ServiceType.RDS, ServiceType.AURORA])
def test_multiple_users_share_database_outputs_without_conflicts(target):
    payload = architecture(target=target)
    second = deepcopy(payload["connections"][0])
    second["connection_config"]["database_user"] = "other_user"
    payload["connections"].append(second)
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected
    policy = json.loads(
        expected["connection-check/iam-policies/source-resource-policy.json"]
    )
    assert len([s for s in policy["Statement"] if "rds-db:connect" in s["Action"]]) == 2


@needs_terraform
@pytest.mark.parametrize("target", [ServiceType.RDS, ServiceType.AURORA])
def test_database_access_validates_without_cycles(target, tmp_path):
    payload = architecture(ServiceType.ECS, target)
    payload["resources"][1]["config"]["manage_master_user_password"] = True
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)


@needs_terraform
@pytest.mark.parametrize("target", [ServiceType.RDS, ServiceType.AURORA])
def test_database_arn_uses_target_partition_region_account_and_resource_id(
    target, tmp_path
):
    import subprocess

    from app.services.connection_handlers.database_access import DatabaseAccessHandler

    ir = IRBuilder().build(
        ArchitectureDescription.model_validate(architecture(target=target))
    )
    result = DatabaseAccessHandler().handle(ir.connections[0], ir)
    expression = next(
        o.value for o in result.outputs if o.name == "iam_database_iam_resource_arn"
    )
    resource = (
        "aws_db_instance.target-resource"
        if target == ServiceType.RDS
        else "aws_rds_cluster.target-resource"
    )
    attribute = "resource_id" if target == ServiceType.RDS else "cluster_resource_id"
    expression = expression.replace(
        resource + ".arn",
        json.dumps("arn:aws-us-gov:rds:us-gov-west-1:987654321098:db:display-name"),
    )
    expression = expression.replace(
        resource + "." + attribute, json.dumps("db-IMMUTABLE")
    )
    evaluated = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input=expression + "\n",
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert evaluated.returncode == 0, evaluated.stderr
    assert (
        json.loads(evaluated.stdout)
        == "arn:aws-us-gov:rds-db:us-gov-west-1:987654321098:dbuser:db-IMMUTABLE"
    )
