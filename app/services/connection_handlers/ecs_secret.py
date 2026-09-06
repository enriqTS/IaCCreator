"""Native ECS secrets injected by the task execution role."""

import json

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.secrets import EcsSecretConfig
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.secret_access import SecretAccessHandler


class EcsSecretHandler(SecretAccessHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        result = super().handle(connection, project)
        if not result.resources:
            return result
        consumer = self._find_instance(connection.source_name, project)
        if consumer is not None:
            consumer.config._inject_runtime_secrets = True
        peers = [
            item
            for item in project.connections
            if item.source_name == connection.source_name
            and item.target_service == ServiceType.SECRETS_MANAGER
        ]
        names = sorted({item.target_name for item in peers})
        bindings: dict[tuple[str, str], str] = {}
        for item in peers:
            config = EcsSecretConfig.model_validate(item.connection_config)
            container = config.container_name or connection.source_name
            environment = (
                config.environment_name
                or "SECRET_" + item.target_name.replace("-", "_").upper()
            )
            key = (container, environment)
            if key in bindings and bindings[key] != item.target_name:
                raise InvalidConnectionConfigError(
                    connection.source_name,
                    item.target_name,
                    "injects_secret",
                    [
                        {
                            "loc": ("environment_name",),
                            "msg": "Two secrets cannot occupy the same container environment variable",
                        },
                    ],
                )
            bindings[key] = item.target_name
        entries = [
            "{ container = "
            + json.dumps(container)
            + ", name = "
            + json.dumps(environment)
            + f", valueFrom = var.runtime_secret_{names.index(secret)}_arn }}"
            for (container, environment), secret in sorted(bindings.items())
        ]
        content = "locals {\n  runtime_secrets = [" + ", ".join(entries) + "]\n}\n"
        result.resources.append(
            self._resource(connection.source_name, "runtime_secrets.tf", content)
        )
        return result
