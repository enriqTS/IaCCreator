"""Serverless IAM grants scope runtime access to one cache and one external user."""

import json
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.elasticache_serverless import (
    ServerlessCacheIamConfig,
)
from app.models.input_models import ArchitectureDescription, ServiceType
from app.models.input_models.elasticache_serverless_config import (
    ElastiCacheServerlessConfig,
)
from app.services.connection_handlers.elasticache_serverless import (
    ServerlessCacheIamHandler,
)
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.test_database_access_connections import generate
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)


def architecture(source=ServiceType.LAMBDA, engine="valkey"):
    payload = connection_architecture(
        resolve_spec(source, ServiceType.ELASTICACHE_SERVERLESS, "authenticates_to", {})
    )
    payload["resources"][1]["config"]["engine"] = engine
    return payload


@given(
    source=st.sampled_from([ServiceType.LAMBDA, ServiceType.ECS]),
    engine=st.sampled_from(["valkey", "redis"]),
    user=st.from_regex(r"[A-Za-z][A-Za-z0-9-]{0,20}", fullmatch=True),
)
def test_login_scopes_cache_and_user_and_exports_tls_signing_metadata(
    source, engine, user
):
    payload = architecture(source, engine)
    payload["connections"][0]["connection_config"]["user_id"] = user
    tree = generate(payload)
    policy = json.loads(
        tree["connection-check/iam-policies/source-resource-policy.json"]
    )
    grants = [s for s in policy["Statement"] if "elasticache:Connect" in s["Action"]]
    assert len(grants) == 1
    assert grants[0]["Action"] == ["elasticache:Connect"]
    assert len(grants[0]["Resource"]) == 2
    assert "${var.serverless_target-resource_cache_arn}" in grants[0]["Resource"]
    assert not any("*" in r for r in grants[0]["Resource"])
    text = "\n".join(tree.values())
    assert f":user:{user.lower()}" in text
    assert f'user_name = "{user.lower()}"' in text
    assert 'resource_type = "ServerlessCache"' in text
    assert "tls = true" in text
    assert "one(aws_elasticache_serverless_cache.target-resource.endpoint).port" in text
    assert "self.full_engine_version" in text
    assert "var.user_group_id" in text
    assert 'aws_elasticache_user"' not in text
    assert 'aws_elasticache_user_group"' not in text
    assert "auth_token" not in text and "secret_string" not in text
    if source == ServiceType.ECS:
        assert "task_role_arn = aws_iam_role.source-resource_role.arn" in text
    project = IRBuilder().build(ArchitectureDescription.model_validate(payload))
    result = ServerlessCacheIamHandler().handle(project.connections[0], project)
    assert next(i for i in result.inputs if i.name.endswith("_port")).type == "number"
    message = ConnectionPreviewer().preview_all(project)[0].issues[0].message
    assert "membership must be verified separately" in message


@pytest.mark.parametrize("user", ["*", "user/*", "${user}", "", "1user", "a" * 41])
def test_invalid_user_identifiers_are_rejected(user):
    with pytest.raises(ValidationError):
        ServerlessCacheIamConfig(user_id=user)


@pytest.mark.parametrize("group", [None, "", " "])
def test_iam_connections_require_an_explicit_external_group(group):
    payload = architecture()
    payload["resources"][1]["config"]["user_group_id"] = group
    with pytest.raises(InvalidConnectionConfigError, match="existing user group"):
        generate(payload)


def test_serverless_model_rejects_memcached_in_this_iam_integration():
    with pytest.raises(ValidationError):
        ElastiCacheServerlessConfig(engine="memcached")


def test_multiple_users_share_cache_metadata_without_duplicate_resources():
    payload = architecture()
    second = deepcopy(payload["connections"][0])
    second["connection_config"]["user_id"] = "other-user"
    payload["connections"].append(second)
    tree = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    text = "\n".join(tree.values())
    assert text.count('resource "aws_elasticache_serverless_cache"') == 1
    grants = json.loads(
        tree["connection-check/iam-policies/source-resource-policy.json"]
    )["Statement"]
    assert len([s for s in grants if "elasticache:Connect" in s["Action"]]) == 2


@needs_terraform
def test_user_arn_preserves_native_partition_region_account(tmp_path):
    project = IRBuilder().build(ArchitectureDescription.model_validate(architecture()))
    result = ServerlessCacheIamHandler().handle(project.connections[0], project)
    expression = next(o.value for o in result.outputs if ":user:" in o.value)
    expression = expression.replace(
        "aws_elasticache_serverless_cache.target-resource.arn",
        json.dumps(
            "arn:aws-us-gov:elasticache:us-gov-west-1:987654321098:serverlesscache:cache"
        ),
    )
    evaluated = subprocess.run(
        ["terraform", "console", "-no-color"],
        cwd=tmp_path,
        input=expression + "\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert evaluated.returncode == 0, evaluated.stderr
    assert (
        json.loads(evaluated.stdout)
        == "arn:aws-us-gov:elasticache:us-gov-west-1:987654321098:user:app-user"
    )


@needs_terraform
@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
@pytest.mark.parametrize("engine", ["valkey", "redis"])
def test_serverless_client_projects_validate_without_cycles(source, engine, tmp_path):
    payload = architecture(source, engine)
    payload["resources"][1]["config"].update(
        subnet_ids=["subnet-external"], security_group_ids=["sg-external"]
    )
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)


@needs_terraform
@pytest.mark.parametrize(
    "engine,version,allowed",
    [
        ("redis", "6.2", False),
        ("redis", "7.0", True),
        ("valkey", "7.0", False),
        ("valkey", "7.2", True),
        ("valkey", "8.0", True),
    ],
)
def test_native_engine_version_guard_enforces_iam_minimum(
    engine, version, allowed, tmp_path
):
    tree = generate(architecture(engine=engine))
    resource = next(
        v for v in tree.values() if 'resource "aws_elasticache_serverless_cache"' in v
    )
    expression = next(
        line.strip().removeprefix("condition = ")
        for line in resource.splitlines()
        if "self.full_engine_version" in line
    )
    expression = expression.replace(
        "self.full_engine_version", json.dumps(version)
    ).replace("self.engine", json.dumps(engine))
    result = subprocess.run(
        ["terraform", "console", "-no-color"],
        cwd=tmp_path,
        input=expression + "\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) is allowed
