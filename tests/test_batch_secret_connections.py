"""Batch job definitions own native injection, not compute environments or job roles."""

import json
import shutil
import subprocess
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.secrets import BatchSecretConfig
from app.models.input_models import ServiceType
from app.models.input_models.batch_job_definition_config import BatchJobDefinitionConfig
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.service_catalog import SERVICE_CATALOG
from tests.hcl_assertions import parse_hcl
from tests.test_secret_connections import architecture, project


def job_file(tree):
    return next(
        content
        for path, content in tree.items()
        if path.endswith("/batch-job-definition.tf")
    )


def test_native_injection_uses_execution_role_not_application_role():
    payload = architecture(ServiceType.BATCH_JOB_DEFINITION)
    payload["resources"][0]["config"]["job_role_arn"] = (
        "arn:aws:iam::123456789012:role/application"
    )
    tree = CodeGenerator().generate(project(payload))
    job = job_file(tree)
    assert 'resource "aws_batch_job_definition"' in job
    assert 'platform_capabilities = ["EC2"]' in job
    assert "executionRoleArn = var.execution_role_arn" in job
    assert "jobRoleArn = var.job_role_arn" in job
    assert "depends_on = [aws_iam_role_policy.runtime_secrets]" in job
    assert "valueFrom = value" in job
    policy = next(
        content
        for path, content in tree.items()
        if path.endswith("/runtime_secrets_policy.tf")
    )
    assert 'element(reverse(split("/", var.execution_role_arn)), 0)' in policy
    assert "job_role_arn" not in policy
    assert 'resource "aws_iam_role"' not in "\n".join(tree.values())


def test_application_role_cannot_substitute_for_execution_role():
    payload = architecture(ServiceType.BATCH_JOB_DEFINITION)
    config = payload["resources"][0]["config"]
    config.pop("execution_role_arn")
    config["job_role_arn"] = "arn:aws:iam::123456789012:role/application"
    with pytest.raises(InvalidConnectionConfigError, match="service role ARN"):
        CodeGenerator().generate(project(payload))


def test_conflicting_bindings_are_rejected():
    payload = architecture(ServiceType.BATCH_JOB_DEFINITION)
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
        {"environment_name": "AWS_BATCH_PASSWORD"},
        {"environment_name": "AWS_BATCHTOKEN"},
        {"environment_name": "bad-name"},
        {"container_name": "job"},
    ],
)
def test_invalid_connection_configuration(config):
    with pytest.raises(ValidationError):
        BatchSecretConfig.model_validate(config)


@pytest.mark.parametrize(
    "config",
    [
        {"environment_variables": {"AWS_BATCH_TOKEN": "invalid"}},
        {"external_secrets": {"AWS_BATCH_TOKEN": "arn:secret"}},
        {"platform_capabilities": ["FARGATE"]},
    ],
)
def test_invalid_native_configuration(config):
    with pytest.raises(ValidationError):
        BatchJobDefinitionConfig(image="example:image", **config)


def test_external_secret_role_is_required_at_generation_not_during_draft_editing():
    config = BatchJobDefinitionConfig(
        image="example:image", external_secrets={"TOKEN": "arn:secret"}
    )
    with pytest.raises(ValueError, match="execution role"):
        config.validate_for_generation()


def test_catalog_schema_and_directions_keep_job_resources_separate():
    metadata = SERVICE_CATALOG[ServiceType.BATCH_JOB_DEFINITION]
    assert (
        metadata.capabilities.diagram
        and metadata.capabilities.terraform
        and metadata.capabilities.connectable
    )
    assert metadata.category == "compute"
    fields = {
        field.name: field for field in BatchJobDefinitionConfig.get_variable_schema()
    }
    assert fields["image"].required
    assert fields["external_secrets"].type == "map"
    assert fields["vcpus"].validation.min == 1
    spec = resolve_spec(
        ServiceType.BATCH_JOB_DEFINITION,
        ServiceType.SECRETS_MANAGER,
        "injects_secret",
        {},
    )
    assert spec.config_model().environment_name is None
    assert (
        resolve_spec(
            ServiceType.BATCH_JOB_DEFINITION, ServiceType.SECRETS_MANAGER, None, {}
        )
        == spec
    )
    assert (
        resolve_spec(
            ServiceType.SECRETS_MANAGER,
            ServiceType.BATCH_JOB_DEFINITION,
            "injects_secret",
            {},
        )
        is None
    )
    assert (
        resolve_spec(
            ServiceType.BATCH, ServiceType.SECRETS_MANAGER, "injects_secret", {}
        )
        is None
    )


def test_unconnected_job_preserves_external_secrets_without_managed_policy():
    payload = architecture(ServiceType.BATCH_JOB_DEFINITION)
    payload["connections"] = []
    payload["resources"][0]["config"]["external_secrets"] = {
        "TOKEN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:external-AbCdEf"
    }
    tree = CodeGenerator().generate(project(payload))
    assert "batch_job_secrets = var.external_secrets" in job_file(tree)
    assert "runtime_secrets" not in "\n".join(tree.values())
    outputs = next(
        content
        for path, content in tree.items()
        if "/batch-job-definition/" in path and path.endswith("/outputs.tf")
    )
    for output in ("job_definition_arn", "job_definition_name", "revision"):
        assert f'output "{output}"' in outputs


def test_container_properties_evaluate_with_managed_and_external_bindings(tmp_path):
    if shutil.which("terraform") is None:
        pytest.skip("terraform binary not installed")
    payload = architecture(ServiceType.BATCH_JOB_DEFINITION)
    payload["connections"][0]["connection_config"] = {"environment_name": "PASSWORD"}
    config = payload["resources"][0]["config"]
    config.update(
        command=["run", "job"],
        vcpus=2,
        memory_mib=2048,
        environment_variables={"PASSWORD": "old", "MODE": "prod"},
        external_secrets={"PASSWORD": "old-secret", "TOKEN": "external-token"},
        job_role_arn="arn:aws:iam::123456789012:role/job-code",
    )
    tree = CodeGenerator().generate(project(payload))
    parsed = parse_hcl(job_file(tree))
    attrs = next(iter(next(iter(parsed["resource"][0].values())).values()))
    expression = attrs["container_properties"][2:-1]
    variables = next(
        content
        for path, content in tree.items()
        if "/batch-job-definition/" in path and path.endswith("/variables.tf")
    )
    secrets = next(
        content
        for path, content in tree.items()
        if path.endswith("/runtime_secrets.tf")
    )
    local = parsed["locals"][0]["batch_job_secrets"][2:-1]
    (tmp_path / "main.tf").write_text(
        variables
        + secrets
        + f"\nlocals {{\n  batch_job_secrets = {local}\n  properties = {expression}\n}}"
    )
    fields = {field.name for field in BatchJobDefinitionConfig.get_variable_schema()}
    values = {key: value for key, value in config.items() if key in fields}
    values["runtime_secret_0_arn"] = "arn:managed-secret"
    (tmp_path / "terraform.tfvars.json").write_text(json.dumps(values))
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input="local.properties\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    properties = json.loads(json.loads(result.stdout))
    assert properties["image"] == config["image"]
    assert properties["command"] == ["run", "job"]
    assert properties["resourceRequirements"] == [
        {"type": "VCPU", "value": "2"},
        {"type": "MEMORY", "value": "2048"},
    ]
    assert properties["environment"] == [{"name": "MODE", "value": "prod"}]
    assert properties["secrets"] == [
        {"name": "PASSWORD", "valueFrom": "arn:managed-secret"},
        {"name": "TOKEN", "valueFrom": "external-token"},
    ]
    assert properties["executionRoleArn"] == config["execution_role_arn"]
    assert properties["jobRoleArn"] == config["job_role_arn"]
