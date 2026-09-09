"""Secrets Manager runtime access and native ECS injection."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.secrets import EcsSecretConfig
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.hcl_assertions import assert_tree_parses

SECRET_CONSUMERS = [
    ServiceType.LAMBDA,
    ServiceType.ECS,
    ServiceType.EC2,
    ServiceType.CODEBUILD,
    ServiceType.APP_RUNNER,
    ServiceType.MWAA,
]


def architecture(service):
    kind = (
        "injects_secret"
        if service in (ServiceType.ECS, ServiceType.CODEBUILD, ServiceType.APP_RUNNER)
        else "reads_secret"
    )
    return connection_architecture(
        resolve_spec(service, ServiceType.SECRETS_MANAGER, kind, {})
    )


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(payload))


@pytest.mark.parametrize(
    "service",
    SECRET_CONSUMERS,
)
def test_runtime_policy_uses_scoped_terraform_references(service):
    ir = project(architecture(service))
    preview = ConnectionPreviewer().preview_all(ir)[0]
    assert preview.issues == []
    assert any(
        resource.resource_type == "aws_iam_role_policy"
        for resource in preview.resources
    )
    contribution = ConnectionProcessor().process_all(ir)
    assert all(
        resource.module == "source-resource" for resource in contribution.resources
    )
    tree = CodeGenerator().generate(ir)
    assert_tree_parses(tree)
    policy = next(
        content
        for path, content in tree.items()
        if path.endswith("/runtime_secrets_policy.tf")
    )
    assert 'Action = [ "secretsmanager:GetSecretValue" ]' in " ".join(policy.split())
    assert "Resource = var.runtime_secret_0_arn" in policy
    if service == ServiceType.CODEBUILD:
        assert 'element(reverse(split("/", var.service_role)), 0)' in policy
    elif service == ServiceType.APP_RUNNER:
        assert 'element(reverse(split("/", var.instance_role_arn)), 0)' in policy
    elif service == ServiceType.MWAA:
        assert 'element(reverse(split("/", var.execution_role_arn)), 0)' in policy
    else:
        assert "aws_iam_role.source-resource_role.id" in policy
    assert "kms:Decrypt" not in policy
    assert "secret_version" not in "\n".join(tree.values())


@pytest.mark.parametrize(
    "service",
    SECRET_CONSUMERS,
)
@given(order=st.permutations([0, 1, 2]))
def test_multiple_and_duplicate_secret_connections_are_deterministic(service, order):
    payload = architecture(service)
    secret = deepcopy(payload["resources"][1])
    secret.update(id="other", name="other-secret")
    payload["resources"].append(secret)
    payload["connections"].append(
        dict(payload["connections"][0], target="other-secret", target_id="other")
    )
    payload["connections"].append(dict(payload["connections"][0]))
    baseline = CodeGenerator().generate(project(payload))
    payload["connections"] = [payload["connections"][index] for index in order]
    ir = project(payload)
    contribution = ConnectionProcessor().process_all(ir)
    paths = [(item.module, item.filename) for item in contribution.resources]
    assert len(paths) == len(set(paths))
    assert dict(CodeGenerator().generate(ir)) == dict(baseline)


@pytest.mark.parametrize(
    "service",
    SECRET_CONSUMERS,
)
@pytest.mark.parametrize("managed", [False, True])
def test_custom_key_decrypt_access(service, managed):
    payload = architecture(service)
    if managed:
        key_payload = connection_architecture(
            resolve_spec(ServiceType.KMS, ServiceType.SECRETS_MANAGER, "encrypts", {})
        )
        key = key_payload["resources"][0]
        key.update(id="key", name="encryption-key")
        payload["resources"].append(key)
        payload["connections"].append(
            dict(
                key_payload["connections"][0], source="encryption-key", source_id="key"
            )
        )
    else:
        payload["resources"][1]["config"]["kms_key_id"] = "alias/external-key"
    tree = CodeGenerator().generate(project(payload))
    assert_tree_parses(tree)
    policy = next(
        content
        for path, content in tree.items()
        if path.endswith("/runtime_secrets_policy.tf")
    )
    assert 'Action = [ "kms:Decrypt" ]' in " ".join(policy.split())
    if managed:
        assert "Resource = var.runtime_secret_0_key_arn" in policy
        assert (
            "runtime_secret_0_key_arn = module.encryption-key.key_arn"
            in tree["connection-check/environments/dev/main.tf"]
        )
    else:
        assert "Resource = data.aws_kms_key.runtime_secret_0.arn" in policy


def test_ecs_injection_uses_execution_role_and_preserves_container_configuration():
    tree = CodeGenerator().generate(project(architecture(ServiceType.ECS)))
    task = next(content for path, content in tree.items() if path.endswith("/ecs.tf"))
    assert "execution_role_arn = aws_iam_role.source-resource_role.arn" in task
    assert "jsondecode(var.container_definitions)" in task
    assert "merge(container," in task
    assert "try(container.secrets, [])" in task
    assert "aws_iam_role_policy.runtime_secrets" in task
    assert "precondition" in task


def test_ecs_rejects_conflicting_bindings():
    payload = architecture(ServiceType.ECS)
    payload["connections"][0]["connection_config"] = {"environment_name": "PASSWORD"}
    secret = deepcopy(payload["resources"][1])
    secret.update(id="other", name="other-secret")
    payload["resources"].append(secret)
    payload["connections"].append(
        dict(payload["connections"][0], target="other-secret", target_id="other")
    )
    with pytest.raises(InvalidConnectionConfigError, match="same container"):
        CodeGenerator().generate(project(payload))


@pytest.mark.parametrize(
    "config",
    [
        {"environment_name": "bad-name"},
        {"container_name": "bad name"},
        {"unknown": True},
    ],
)
def test_invalid_injection_config_is_rejected(config):
    with pytest.raises(ValidationError):
        EcsSecretConfig.model_validate(config)


def test_reverse_direction_is_unsupported():
    assert (
        resolve_spec(
            ServiceType.SECRETS_MANAGER, ServiceType.LAMBDA, "reads_secret", {}
        )
        is None
    )


def test_ecs_merge_evaluates_with_external_container_definitions(tmp_path):
    import json
    import shutil
    import subprocess

    from app.generators.ecs_secrets import secret_task_attributes
    from app.generators.hcl_renderer import HCLRenderer

    if shutil.which("terraform") is None:
        pytest.skip("terraform binary not installed")
    containers = [
        {
            "name": "worker",
            "image": "custom:image",
            "environment": [
                {"name": "PASSWORD", "value": "old"},
                {"name": "MODE", "value": "prod"},
            ],
            "secrets": [
                {"name": "PASSWORD", "valueFrom": "external-old"},
                {"name": "TOKEN", "valueFrom": "external-token"},
            ],
        },
        {"name": "sidecar", "image": "sidecar:image"},
    ]
    content = HCLRenderer().render_variable(
        "container_definitions",
        "string",
        "Custom containers",
        default=json.dumps(containers),
    )
    content += 'locals { runtime_secrets = [{container = "worker", name = "PASSWORD", valueFrom = "managed-arn"}] }'
    (tmp_path / "main.tf").write_text(content)
    expression = secret_task_attributes("worker")["container_definitions"]
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input=expression + "\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    rendered = json.loads(json.loads(result.stdout))
    assert rendered[0]["image"] == "custom:image"
    assert rendered[0]["environment"] == [{"name": "MODE", "value": "prod"}]
    assert rendered[0]["secrets"] == [
        {"name": "TOKEN", "valueFrom": "external-token"},
        {"name": "PASSWORD", "valueFrom": "managed-arn"},
    ]
    assert rendered[1]["secrets"] == []
    assert rendered[1]["image"] == "sidecar:image"


@pytest.mark.parametrize(
    "service",
    SECRET_CONSUMERS,
)
def test_encrypted_secret_project_validates(tmp_path, service):
    from tests.test_generated_project_validates import (
        _init_args,
        _run_terraform,
        _write_tree,
        needs_terraform,
    )

    if needs_terraform.args[0]:
        pytest.skip("terraform binary not installed")
    payload = architecture(service)
    key_payload = connection_architecture(
        resolve_spec(ServiceType.KMS, ServiceType.SECRETS_MANAGER, "encrypts", {})
    )
    key = key_payload["resources"][0]
    key.update(id="key", name="encryption-key")
    payload["resources"].append(key)
    payload["connections"].append(
        dict(key_payload["connections"][0], source="encryption-key", source_id="key")
    )
    _write_tree(tmp_path, CodeGenerator().generate(project(payload)))
    environment = tmp_path / "connection-check/environments/dev"
    _run_terraform(_init_args(), environment)
    _run_terraform(["validate", "-no-color"], environment)


def test_ec2_secret_access_creates_and_attaches_one_profile():
    ir = project(architecture(ServiceType.EC2))
    preview = ConnectionPreviewer().preview_all(ir)[0]
    assert {resource.resource_type for resource in preview.resources} == {
        "aws_iam_role",
        "aws_iam_instance_profile",
        "aws_iam_role_policy",
    }
    tree = CodeGenerator().generate(ir)
    instance = next(
        content for path, content in tree.items() if path.endswith("/ec2.tf")
    )
    assert (
        "iam_instance_profile = aws_iam_instance_profile.runtime_secrets.name"
        in instance
    )
    assert "depends_on = [aws_iam_role_policy.runtime_secrets]" in instance
    credentials = next(
        content
        for path, content in tree.items()
        if path.endswith("/runtime_secrets_role.tf")
    )
    assert "ec2.amazonaws.com" in credentials
    assert "role = aws_iam_role.source-resource_role.name" in credentials


def test_unconnected_ec2_does_not_create_secret_credentials():
    payload = architecture(ServiceType.EC2)
    payload["connections"] = []
    tree = CodeGenerator().generate(project(payload))
    assert not any("runtime_secrets" in path for path in tree)
    instance = next(
        content for path, content in tree.items() if path.endswith("/ec2.tf")
    )
    assert "iam_instance_profile" not in instance
