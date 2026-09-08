"""Native CodeBuild secret injection and external service-role ownership."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.secrets import CodeBuildSecretConfig
from app.models.input_models import ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from tests.test_secret_connections import architecture, project


def test_injection_uses_native_environment_and_external_role():
    payload = architecture(ServiceType.CODEBUILD)
    payload["connections"][0]["connection_config"] = {"environment_name": "PASSWORD"}
    tree = CodeGenerator().generate(project(payload))
    build = next(
        content for path, content in tree.items() if path.endswith("/codebuild.tf")
    )
    assert 'dynamic "environment_variable"' in build
    assert 'type = "SECRETS_MANAGER"' in build
    assert "value = environment_variable.value" in build
    assert "service_role = var.service_role" in build
    assert "depends_on = [aws_iam_role_policy.runtime_secrets]" in build
    bindings = next(
        content
        for path, content in tree.items()
        if path.endswith("/runtime_secrets.tf")
    )
    assert '"PASSWORD" = var.runtime_secret_0_arn' in bindings
    assert 'resource "aws_iam_role"' not in "\n".join(tree.values())


def test_missing_service_role_is_rejected():
    payload = architecture(ServiceType.CODEBUILD)
    payload["resources"][0]["config"].pop("service_role")
    with pytest.raises(InvalidConnectionConfigError, match="service role ARN"):
        CodeGenerator().generate(project(payload))


def test_conflicting_environment_bindings_are_rejected():
    payload = architecture(ServiceType.CODEBUILD)
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
        {"environment_name": "bad-name"},
        {"environment_name": "CODEBUILD_TOKEN"},
        {"container_name": "build"},
    ],
)
def test_invalid_config(config):
    with pytest.raises(ValidationError):
        CodeBuildSecretConfig.model_validate(config)


def test_schema_default_and_direction():
    spec = resolve_spec(
        ServiceType.CODEBUILD, ServiceType.SECRETS_MANAGER, "injects_secret", {}
    )
    assert spec.config_model().environment_name is None
    assert [field.key for field in spec.config_model.get_field_schema()] == [
        "environment_name"
    ]
    assert (
        resolve_spec(ServiceType.CODEBUILD, ServiceType.SECRETS_MANAGER, None, {})
        == spec
    )
    assert (
        resolve_spec(
            ServiceType.SECRETS_MANAGER, ServiceType.CODEBUILD, "injects_secret", {}
        )
        is None
    )
    assert (
        resolve_spec(
            ServiceType.CODEBUILD, ServiceType.SECRETS_MANAGER, "legacy", {}
        )
        == spec
    )


def test_unconnected_project_does_not_get_secret_bindings_or_policy():
    payload = architecture(ServiceType.CODEBUILD)
    payload["connections"] = []
    tree = CodeGenerator().generate(project(payload))
    assert "runtime_secrets" not in "\n".join(tree.values())
