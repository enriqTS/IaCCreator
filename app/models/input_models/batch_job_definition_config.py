"""Single-container EC2 Batch job configuration, separate from compute environments."""

from typing import Literal

from pydantic import ConfigDict, PrivateAttr, field_validator

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField, ValidationRule


class BatchJobDefinitionConfig(BaseServiceConfig):
    model_config = ConfigDict(extra="forbid")
    service_type: Literal[ServiceType.BATCH_JOB_DEFINITION] = (
        ServiceType.BATCH_JOB_DEFINITION
    )
    image: str = TerraformField(..., description="Container image URI")
    vcpus: int = TerraformField(
        1, description="EC2 job vCPU count", validation=ValidationRule(min=1)
    )
    memory_mib: int = TerraformField(
        1024, description="Container memory in MiB", validation=ValidationRule(min=4)
    )
    command: list[str] = TerraformField([], description="Container command override")
    execution_role_arn: str | None = TerraformField(
        None,
        group="IAM",
        description="Task execution role trusted by ecs-tasks.amazonaws.com; used for secret injection",
    )
    job_role_arn: str | None = TerraformField(
        None,
        group="IAM",
        description="Optional application role for job code, separate from the execution role",
    )
    environment_variables: dict[str, str] = TerraformField(
        {},
        group="Environment",
        description="Plaintext environment variables; secret bindings replace matching names",
    )
    external_secrets: dict[str, str] = TerraformField(
        {},
        group="Environment",
        description="External secret ARNs by environment variable name; permissions remain externally managed",
    )
    _inject_runtime_secrets: bool = PrivateAttr(default=False)

    @field_validator("environment_variables", "external_secrets")
    @classmethod
    def reject_reserved_names(cls, values: dict[str, str]) -> dict[str, str]:
        if any(not name or name.startswith("AWS_BATCH") for name in values):
            raise ValueError(
                "Environment names must be nonempty and cannot start with AWS_BATCH"
            )
        return values

    def validate_for_generation(self) -> None:
        if self.external_secrets and not self.execution_role_arn:
            raise ValueError("External secrets require a task execution role ARN")
