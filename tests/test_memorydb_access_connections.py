"""MemoryDB IAM access validates existing identities without handling passwords."""

import json
import re
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.generators.memorydb_iam import client_lifecycle, existing_user
from app.models.connection_configs.memorydb import MemoryDbIamConfig
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)


def architecture(source=ServiceType.LAMBDA):
    return connection_architecture(
        resolve_spec(source, ServiceType.MEMORYDB, "authenticates_to", {})
    )


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


def generate(payload):
    return CodeGenerator().generate(project(payload))


@given(
    source=st.sampled_from([ServiceType.LAMBDA, ServiceType.ECS]),
    username=st.from_regex(r"[a-zA-Z][a-zA-Z0-9]{0,15}", fullmatch=True),
)
def test_login_grants_require_exact_cluster_and_existing_user(source, username):
    payload = architecture(source)
    payload["connections"][0]["connection_config"]["user_name"] = username
    tree = generate(payload)
    policy = json.loads(
        tree["connection-check/iam-policies/source-resource-policy.json"]
    )
    grants = [s for s in policy["Statement"] if "memorydb:Connect" in s["Action"]]
    assert len(grants) == 1 and grants[0]["Action"] == ["memorydb:Connect"]
    resources = grants[0]["Resource"]
    assert len(resources) == 2
    assert "${var.memorydb_target-resource_cluster_arn}" in resources
    assert any("_iam_user_" in value for value in resources)
    assert not any("*" in value for value in resources)
    text = "\n".join(tree.values())
    assert f'user_name = "{username.lower()}"' in text
    assert 'data "aws_memorydb_user"' in text
    assert 'data "aws_memorydb_acl"' in text
    assert 'resource "aws_memorydb_user"' not in text
    assert 'resource "aws_memorydb_acl"' not in text
    assert "secret_string" not in text
    assert "memorydb:CreateUser" not in text
    assert 'one(self.authentication_mode).type == "iam"' in text
    assert (
        "contains(data.aws_memorydb_acl.iam_client.user_names, self.user_name)" in text
    )
    for field in ["host", "port", "region", "cluster_name"]:
        assert f"module.target-resource.iam_client_{field}" in text
    assert "var.tls_enabled &&" in text
    assert "self.engine_version" in text
    if source == ServiceType.ECS:
        assert "task_role_arn = aws_iam_role.source-resource_role.arn" in text
    assert ConnectionPreviewer().preview_all(project(payload))[0].issues


@pytest.mark.parametrize("username", ["*", "a/b", "a?", "", "1name", "a_b", "${user}"])
def test_user_selector_rejects_invalid_identity_and_wildcards(username):
    with pytest.raises(ValidationError):
        MemoryDbIamConfig(user_name=username)


@pytest.mark.parametrize(
    "config",
    [
        {"tls_enabled": False},
        {"acl_name": "open-access"},
        {"acl_name": ""},
        {"engine_version": "6.2"},
        {"engine_version": "old"},
    ],
)
def test_missing_native_iam_prerequisites_are_rejected(config):
    payload = architecture()
    payload["resources"][1]["config"].update(config)
    with pytest.raises(
        InvalidConnectionConfigError, match="MemoryDB IAM login requires"
    ):
        generate(payload)


@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_users_share_acl_and_cluster_metadata_without_duplicate_reads(source):
    payload = architecture(source)
    alias = deepcopy(payload["connections"][0])
    alias["connection_config"]["user_name"] = "APP-USER"
    other = deepcopy(alias)
    other["connection_config"]["user_name"] = "other-user"
    payload["connections"].extend([alias, other])
    expected = generate(payload)
    text = "\n".join(expected.values())
    assert text.count('data "aws_memorydb_acl"') == 1
    assert text.count('data "aws_memorydb_user"') == 2
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected


def test_unconnected_cluster_preserves_external_configuration():
    payload = architecture()
    payload["connections"] = []
    text = "\n".join(generate(payload).values())
    assert 'data "aws_memorydb_user"' not in text
    assert "postcondition" not in text
    assert "acl_name = var.acl_name" in text


@needs_terraform
@pytest.mark.parametrize(
    "mode,member",
    [("iam", True), ("iam", False), ("password", True), ("password", False)],
)
def test_existing_user_checks_evaluate_iam_mode_and_membership(mode, member, tmp_path):
    conditions = re.findall(r"condition = (.*)", existing_user("example", "app-user"))
    values = {
        "self.authentication_mode": json.dumps([{"type": mode}]),
        "self.user_name": json.dumps("app-user"),
        "data.aws_memorydb_acl.iam_client.user_names": json.dumps(
            ["app-user"] if member else ["other-user"]
        ),
    }
    expressions = []
    for condition in conditions:
        for key, value in values.items():
            condition = condition.replace(key, value)
        expressions.append(condition)
    expression = "jsonencode([" + ", ".join(expressions) + "])"
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input=expression + "\n",
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(json.loads(result.stdout)) == [mode == "iam", member]


@needs_terraform
def test_engine_and_tls_guards_evaluate_overrides(tmp_path):
    lifecycle = client_lifecycle(True)
    conditions = [str(item["condition"]) for item in lifecycle["precondition"]]
    conditions.append(str(lifecycle["postcondition"]["condition"]))
    expression = "jsonencode([" + ", ".join(conditions) + "])"
    expression = (
        expression.replace("var.tls_enabled", "false")
        .replace("var.acl_name", '"open-access"')
        .replace("var.engine_version", '"6.2"')
        .replace("self.engine_version", '"7.1"')
    )
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input=expression + "\n",
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(json.loads(result.stdout)) == [False, False, True]


@needs_terraform
@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_existing_identity_access_validates_without_cycles(source, tmp_path):
    payload = architecture(source)
    payload["resources"][1]["config"]["engine_version"] = "7.1"
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
