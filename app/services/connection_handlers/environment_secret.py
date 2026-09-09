"""Native secret environment bindings on an external runtime role."""

import json

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.secrets import EnvironmentSecretConfig
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.external_role_secret import (
    ExternalRoleSecretAccessHandler,
)


class EnvironmentSecretHandler(ExternalRoleSecretAccessHandler):
    def __init__(
        self, config_model: type[EnvironmentSecretConfig], role_field: str, label: str
    ) -> None:
        super().__init__(role_field, label)
        self._config_model = config_model

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        result = super().handle(connection, project)
        if not result.resources:
            return result
        peers = [
            item
            for item in project.connections
            if item.source_name == connection.source_name
            and item.target_service == ServiceType.SECRETS_MANAGER
        ]
        names = sorted({item.target_name for item in peers})
        bindings: dict[str, str] = {}
        for item in peers:
            config = self._config_model.model_validate(item.connection_config)
            environment = (
                config.environment_name
                or "SECRET_" + item.target_name.replace("-", "_").upper()
            )
            if environment in bindings and bindings[environment] != item.target_name:
                raise InvalidConnectionConfigError(
                    connection.source_name,
                    item.target_name,
                    connection.connection_type,
                    [
                        {
                            "loc": ("environment_name",),
                            "msg": "Two secrets cannot occupy the same environment variable",
                        }
                    ],
                )
            bindings[environment] = item.target_name
        instance = self._find_instance(connection.source_name, project)
        instance.config._inject_runtime_secrets = True
        entries = [
            json.dumps(environment) + f" = var.runtime_secret_{names.index(secret)}_arn"
            for environment, secret in sorted(bindings.items())
        ]
        result.resources.append(
            self._resource(
                connection.source_name,
                "runtime_secrets.tf",
                "locals {\n  runtime_secrets = {\n    "
                + "\n    ".join(entries)
                + "\n  }\n}\n",
            )
        )
        return result
