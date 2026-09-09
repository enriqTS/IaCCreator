"""MWAA runtime reads are scoped grants, not native secret injection."""

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from tests.test_secret_connections import architecture, project


def test_mwaa_uses_external_role_without_injecting_secret_values():
    tree = CodeGenerator().generate(project(architecture(ServiceType.MWAA)))
    environment = next(
        content for path, content in tree.items() if path.endswith("/mwaa.tf")
    )
    assert "execution_role_arn = var.execution_role_arn" in environment
    assert "depends_on = [aws_iam_role_policy.runtime_secrets]" in environment
    policy = next(
        content
        for path, content in tree.items()
        if path.endswith("/runtime_secrets_policy.tf")
    )
    assert 'role = element(reverse(split("/", var.execution_role_arn)), 0)' in policy
    all_hcl = "\n".join(tree.values())
    assert 'resource "aws_iam_role"' not in all_hcl
    assert "airflow_configuration_options" not in environment
    assert "runtime_environment_secrets" not in all_hcl
    assert "secret_version" not in all_hcl


@pytest.mark.parametrize("role", ["", None])
def test_missing_execution_role_is_rejected(role):
    payload = architecture(ServiceType.MWAA)
    if role is None:
        payload["resources"][0]["config"].pop("execution_role_arn")
    else:
        payload["resources"][0]["config"]["execution_role_arn"] = role
    with pytest.raises(InvalidConnectionConfigError, match="service role ARN"):
        CodeGenerator().generate(project(payload))


def test_unconnected_mwaa_does_not_acquire_secret_dependencies():
    payload = architecture(ServiceType.MWAA)
    payload["connections"] = []
    tree = CodeGenerator().generate(project(payload))
    assert "runtime_secrets" not in "\n".join(tree.values())


def test_read_access_schema_and_legacy_pair_resolution():
    spec = resolve_spec(
        ServiceType.MWAA, ServiceType.SECRETS_MANAGER, "reads_secret", {}
    )
    assert spec.config_model.get_field_schema() == []
    assert resolve_spec(ServiceType.MWAA, ServiceType.SECRETS_MANAGER, None, {}) == spec
    assert (
        resolve_spec(ServiceType.SECRETS_MANAGER, ServiceType.MWAA, "reads_secret", {})
        is None
    )
    with pytest.raises(ValidationError):
        spec.config_model.model_validate({"environment_name": "PASSWORD"})
