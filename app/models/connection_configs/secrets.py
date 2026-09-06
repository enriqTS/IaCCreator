"""Runtime secret injection configuration."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class EcsSecretConfig(BaseConnectionConfig):
    environment_name: str | None = ConnectionField(
        None,
        label="Environment variable",
        description="Defaults to SECRET_ followed by the secret node name",
        validation=ValidationRule(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$"),
    )
    container_name: str | None = ConnectionField(
        None,
        label="Container",
        description="Defaults to the ECS node name",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9_-]+$"),
    )
