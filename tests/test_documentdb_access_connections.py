"""DocumentDB identity bindings do not confuse IAM policies with database grants."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
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
        resolve_spec(source, ServiceType.DOCUMENTDB, None, {})
    )


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


def generate(payload):
    return CodeGenerator().generate(project(payload))


@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_client_metadata_uses_runtime_identity_without_database_iam_grants(source):
    payload = architecture(source)
    tree = generate(payload)
    text = "\n".join(tree.values())
    assert "role_arn = aws_iam_role.source-resource_role.arn" in text
    assert 'auth_source = "$external"' in text
    assert 'auth_mechanism = "MONGODB-AWS"' in text
    assert "tls = true" in text
    assert "retry_writes = false" in text
    assert "aws_docdb_cluster.target-resource.reader_endpoint" in text
    assert "tostring(aws_docdb_cluster.target-resource.port)" in text
    assert 'condition = var.engine_version == "5.0"' in text
    assert 'condition = self.engine_version == "5.0"' in text
    if source == ServiceType.ECS:
        assert "task_role_arn = aws_iam_role.source-resource_role.arn" in text
    policy_path = "connection-check/iam-policies/source-resource-policy.json"
    payload["connections"] = []
    baseline = generate(payload)
    assert tree[policy_path] == baseline[policy_path]
    assert "iam_database_authentication_enabled" not in text
    assert "master_password" not in text
    assert "secretsmanager:GetSecretValue" not in text
    assert "aws_docdb_cluster_instance" not in text
    payload = architecture(source)
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert any("$external" in issue.message for issue in preview.issues)


@given(version=st.one_of(st.none(), st.text(max_size=20).filter(lambda v: v != "5.0")))
def test_only_explicit_supported_engine_version_is_accepted(version):
    payload = architecture()
    payload["resources"][1]["config"]["engine_version"] = version
    with pytest.raises(InvalidConnectionConfigError, match="5.0"):
        generate(payload)


@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_multiple_clusters_and_duplicate_connections_are_deterministic(source):
    payload = architecture(source)
    target = deepcopy(payload["resources"][1])
    target["id"] = "other"
    target["name"] = "other-cluster"
    payload["resources"].append(target)
    connection = deepcopy(payload["connections"][0])
    connection["target"] = "other-cluster"
    connection["target_id"] = "other"
    payload["connections"].append(connection)
    tree = generate(payload)
    assert "documentdb_other-cluster_iam_client" in "\n".join(tree.values())
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


def test_default_schema_has_no_password_or_misleading_permission_selector():
    spec = resolve_spec(ServiceType.LAMBDA, ServiceType.DOCUMENTDB, None, {})
    assert spec.connection_type == "authenticates_to"
    assert spec.config_model.get_field_schema() == []


def test_shared_cluster_preserves_distinct_consumer_role_identities():
    payload = architecture()
    ecs = architecture(ServiceType.ECS)["resources"][0]
    ecs["id"] = "ecs-client"
    ecs["name"] = "ecs-client"
    payload["resources"].append(ecs)
    connection = deepcopy(payload["connections"][0])
    connection["source"] = "ecs-client"
    connection["source_id"] = "ecs-client"
    payload["connections"].append(connection)
    tree = generate(payload)
    text = "\n".join(tree.values())
    assert "role_arn = aws_iam_role.source-resource_role.arn" in text
    assert "role_arn = aws_iam_role.ecs-client_role.arn" in text
    assert text.count('output "iam_client_host"') == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_unconnected_ecs_does_not_attach_a_task_role():
    payload = architecture(ServiceType.ECS)
    payload["connections"] = []
    text = "\n".join(generate(payload).values())
    assert "task_role_arn" not in text
    assert "postcondition" not in text


@needs_terraform
@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_documentdb_binding_validates_without_dependency_cycles(source, tmp_path):
    _write_tree(tmp_path, generate(architecture(source)))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
