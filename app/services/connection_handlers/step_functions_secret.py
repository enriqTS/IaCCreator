"""Workflow-owned Secrets Manager SDK tasks and scoped execution-role permissions."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.generators.step_functions_secrets import secret_workflow_locals
from app.models.connection_configs.workflows import StepFunctionsSecretConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.models.workflow_states import placeholder_errors
from app.services.connection_handlers.external_role_secret import (
    ExternalRoleSecretAccessHandler,
)


class StepFunctionsSecretHandler(ExternalRoleSecretAccessHandler):
    def __init__(self) -> None:
        super().__init__("role_arn", "Step Functions")

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The task returns secret material into workflow data. Restrict execution-history access and avoid execution-data logging.",
            )
        ]

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
        secrets = sorted({item.target_name for item in peers})
        bindings: dict[str, str] = {}
        for item in peers:
            config = StepFunctionsSecretConfig.model_validate(item.connection_config)
            if (
                config.state_name in bindings
                and bindings[config.state_name] != item.target_name
            ):
                raise InvalidConnectionConfigError(
                    connection.source_name,
                    item.target_name,
                    connection.connection_type,
                    [
                        {
                            "loc": ("state_name",),
                            "msg": "Two secrets cannot replace the same workflow state",
                        }
                    ],
                )
            bindings[config.state_name] = item.target_name
        instance = self._find_instance(connection.source_name, project)
        errors = placeholder_errors(instance.config.definition, set(bindings))
        if errors:
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [{"loc": ("definition",), "msg": error} for error in errors],
            )
        instance.config._reads_runtime_secrets = True
        content = secret_workflow_locals(
            {
                name: Expr(f"var.runtime_secret_{secrets.index(secret)}_arn")
                for name, secret in sorted(bindings.items())
            }
        )
        result.resources.append(
            self._resource(connection.source_name, "secret_tasks.tf", content)
        )
        return result
