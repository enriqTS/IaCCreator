"""Runtime secret injection configuration."""

from pydantic import field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class EnvironmentSecretConfig(BaseConnectionConfig):
    environment_name: str | None = ConnectionField(
        None,
        label="Environment variable",
        description="Defaults to SECRET_ followed by the secret node name",
        validation=ValidationRule(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$"),
    )


class CodeBuildSecretConfig(EnvironmentSecretConfig):
    @field_validator("environment_name")
    @classmethod
    def reject_reserved_prefix(cls, value: str | None) -> str | None:
        if value is not None and value.startswith("CODEBUILD_"):
            raise ValueError("CODEBUILD_ is reserved by CodeBuild")
        return value


class EcsSecretConfig(EnvironmentSecretConfig):
    container_name: str | None = ConnectionField(
        None,
        label="Container",
        description="Defaults to the ECS node name",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9_-]+$"),
    )
