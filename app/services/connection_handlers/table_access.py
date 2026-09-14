"""Shared table references and runtime metadata for database clients."""

import hashlib
from typing import Literal

from app.generators.hcl_renderer import Expr
from app.models.connection_configs._base import BaseConnectionConfig
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class TableAccessHandler(BaseConnectionHandler):
    config_model: type[BaseConnectionConfig]
    resource_type: str
    database_name_attribute: str
    read_actions: list[str]
    write_actions: list[str]

    def __init__(self, access: Literal["read", "write"]):
        super().__init__()
        self._actions = self.read_actions if access == "read" else self.write_actions

    def supporting_permissions(
        self, connection: ConnectionIR, resource: str
    ) -> ConnectionContribution:
        raise NotImplementedError

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = self.config_model.model_validate(connection.connection_config)
        source, target = connection.source_name, connection.target_name
        resource = f"{self.resource_type}.{target}"
        identity = hashlib.sha256(
            repr((target, config.table_name)).encode()
        ).hexdigest()[:16]
        binding = f"table_access_{identity}"
        result = self.supporting_permissions(connection, resource)
        table = self._renderer.render_expression(config.table_name)
        expressions = {
            "table_arn": f'format("%s/table/%s", trimsuffix({resource}.arn, "/"), {table})',
            "database_name": f"{resource}.{self.database_name_attribute}",
            "region": f'split(":", {resource}.arn)[3]',
        }
        for field, expression in expressions.items():
            variable = f"{binding}_{field}"
            result.outputs.append(self._output(target, variable, expression))
            result.inputs.append(
                ModuleInput(
                    module=source, name=variable, value=f"module.{target}.{variable}"
                )
            )
        metadata = {field: Expr(f"var.{binding}_{field}") for field in expressions}
        metadata["table_name"] = config.table_name
        result.outputs.append(
            self._output(
                source,
                binding,
                self._renderer.render_expression(metadata),
                "Existing table client configuration",
            )
        )
        result.iam.append(
            self._grant(
                source,
                IAMStatement(
                    actions=self._actions,
                    resources=["${var." + binding + "_table_arn}"],
                ),
            )
        )
        return result
