"""App Runner native secret bindings and runtime-role separation."""

import json
import shutil
import subprocess
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.secrets import AppRunnerSecretConfig
from app.models.input_models import ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from tests.test_secret_connections import architecture, project


def service_file(tree):
    return next(
        content for path, content in tree.items() if path.endswith("/app-runner.tf")
    )


def test_native_injection_uses_runtime_role_not_image_pull_role():
    payload = architecture(ServiceType.APP_RUNNER)
    payload["resources"][0]["config"].update(
        image_repository_type="ECR",
        access_role_arn="arn:aws:iam::123456789012:role/image-pull",
        runtime_environment_secrets={
            "EXTERNAL": "arn:aws:secretsmanager:us-east-1:123456789012:secret:external-AbCdEf"
        },
    )
    tree = CodeGenerator().generate(project(payload))
    service = service_file(tree)
    assert "instance_role_arn = var.instance_role_arn" in service
    assert "access_role_arn = var.access_role_arn" in service
    assert (
        "runtime_environment_secrets = merge(var.runtime_environment_secrets, local.runtime_secrets)"
        in service
    )
    assert "depends_on = [aws_iam_role_policy.runtime_secrets]" in service
    policy = next(
        content
        for path, content in tree.items()
        if path.endswith("/runtime_secrets_policy.tf")
    )
    assert 'element(reverse(split("/", var.instance_role_arn)), 0)' in policy
    assert "access_role_arn" not in policy


def test_public_image_disables_unsupported_automatic_deployments():
    service = service_file(
        CodeGenerator().generate(project(architecture(ServiceType.APP_RUNNER)))
    )
    assert "auto_deployments_enabled = false" in service
    assert "authentication_configuration" not in service


def test_missing_runtime_role_is_rejected_even_with_image_pull_role():
    payload = architecture(ServiceType.APP_RUNNER)
    config = payload["resources"][0]["config"]
    config.pop("instance_role_arn")
    config["access_role_arn"] = "arn:aws:iam::123456789012:role/image-pull"
    with pytest.raises(InvalidConnectionConfigError, match="service role ARN"):
        CodeGenerator().generate(project(payload))


def test_conflicting_environment_names_are_rejected():
    payload = architecture(ServiceType.APP_RUNNER)
    payload["connections"][0]["connection_config"] = {"environment_name": "PASSWORD"}
    secret = deepcopy(payload["resources"][1])
    secret.update(id="other", name="other-secret")
    payload["resources"].append(secret)
    payload["connections"].append(
        dict(payload["connections"][0], target="other-secret", target_id="other")
    )
    with pytest.raises(InvalidConnectionConfigError, match="same environment variable"):
        CodeGenerator().generate(project(payload))


@pytest.mark.parametrize(
    "config",
    [
        {"environment_name": "PORT"},
        {"environment_name": "AWSAPPRUNNER_TOKEN"},
        {"environment_name": "bad-name"},
        {"container_name": "app"},
    ],
)
def test_invalid_configuration(config):
    with pytest.raises(ValidationError):
        AppRunnerSecretConfig.model_validate(config)


def test_service_schemas_expose_native_injection_inputs():
    from app.models.input_models.app_runner_config import AppRunnerConfig
    from app.models.input_models.codebuild_config import CodeBuildConfig

    assert {
        "image_repository_type",
        "access_role_arn",
        "instance_role_arn",
        "runtime_environment_secrets",
    } <= {field.name for field in AppRunnerConfig.get_variable_schema()}
    assert {"image", "compute_type", "buildspec"} <= {
        field.name for field in CodeBuildConfig.get_variable_schema()
    }


def test_schema_defaults_legacy_resolution_and_reverse_direction():
    spec = resolve_spec(
        ServiceType.APP_RUNNER, ServiceType.SECRETS_MANAGER, "injects_secret", {}
    )
    assert spec.config_model().environment_name is None
    assert [field.key for field in spec.config_model.get_field_schema()] == [
        "environment_name"
    ]
    assert (
        resolve_spec(ServiceType.APP_RUNNER, ServiceType.SECRETS_MANAGER, "legacy", {})
        == spec
    )
    assert (
        resolve_spec(
            ServiceType.SECRETS_MANAGER, ServiceType.APP_RUNNER, "injects_secret", {}
        )
        is None
    )


def test_unconnected_service_preserves_external_secrets_without_managed_policy():
    payload = architecture(ServiceType.APP_RUNNER)
    payload["connections"] = []
    tree = CodeGenerator().generate(project(payload))
    assert (
        "runtime_environment_secrets = var.runtime_environment_secrets"
        in service_file(tree)
    )
    assert "runtime_secrets" not in "\n".join(tree.values())


def test_managed_bindings_override_only_matching_external_names(tmp_path):
    if shutil.which("terraform") is None:
        pytest.skip("terraform binary not installed")
    payload = architecture(ServiceType.APP_RUNNER)
    payload["connections"][0]["connection_config"] = {"environment_name": "PASSWORD"}
    tree = CodeGenerator().generate(project(payload))
    service = service_file(tree)
    expression = next(
        line.split(" = ", 1)[1]
        for line in service.splitlines()
        if "runtime_environment_secrets =" in line
    )
    (tmp_path / "main.tf").write_text(
        'variable "runtime_environment_secrets" { default = { PASSWORD = "old", TOKEN = "external" } }\nlocals { runtime_secrets = { PASSWORD = "managed" } }'
    )
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input=f"jsonencode({expression})\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(json.loads(result.stdout)) == {
        "PASSWORD": "managed",
        "TOKEN": "external",
    }
