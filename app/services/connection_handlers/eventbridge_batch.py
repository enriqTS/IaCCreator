"""EventBridge submits a generated Batch job to the connected queue."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.eventbridge_batch import EventBridgeBatchConfig
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.eventbridge_role_target import (
    EventBridgeRoleTargetHandler,
)


class EventBridgeBatchHandler(EventBridgeRoleTargetHandler):
    config_model = EventBridgeBatchConfig

    def __init__(self):
        super().__init__(
            "batch",
            "batch:SubmitJob",
            "job_queue_arn",
            "Submits the selected Batch job definition to the connected job queue. Configure compute capacity, retries, dead-letter handling, and monitoring separately.",
        )

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = self.config_model.model_validate(connection.connection_config)
        definition = self._find_instance(config.job_definition_name, project)
        target = self._find_instance(connection.target_name, project)
        if (
            definition is None
            or definition.service_type != ServiceType.BATCH_JOB_DEFINITION
        ):
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("job_definition_name",),
                        "msg": "Select a Batch job definition node in this diagram",
                    }
                ],
            )
        if (
            target.config.batch_compute_environment_type != "UNMANAGED"
            or not target.config.service_role_arn
        ):
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("batch_compute_environment_type",),
                        "msg": "Batch rule targets require an unmanaged compute environment, a service role, and external capacity",
                    }
                ],
            )
        if not target.config.compute_environment_name:
            target.config.compute_environment_name = connection.target_name.replace(
                "-", "_"
            )
        if not target.config.job_queue_name:
            target.config.job_queue_name = f"{connection.target_name}-queue"
        return super().handle(connection, project)

    def additional_inputs(
        self,
        rule: str,
        destination: str,
        identifier: str,
        config: EventBridgeBatchConfig,
    ) -> list[ModuleInput]:
        return [
            ModuleInput(
                module=rule,
                name=f"{identifier}_job_definition_arn",
                value=f"module.{config.job_definition_name}.job_definition_arn",
            )
        ]

    def policy_statements(
        self,
        statements: list[dict],
        variable: str,
        identifier: str,
        config: EventBridgeBatchConfig,
    ) -> list[dict]:
        statements[0]["Resource"].append(Expr(f"var.{identifier}_job_definition_arn"))
        return statements

    def target_attributes(
        self, config: EventBridgeBatchConfig, identifier: str
    ) -> dict:
        attrs = {
            "job_definition": Expr(f"var.{identifier}_job_definition_arn"),
            "job_name": config.job_name,
        }
        if config.array_size is not None:
            attrs["array_size"] = config.array_size
        if config.job_attempts is not None:
            attrs["job_attempts"] = config.job_attempts
        return {"batch_target": attrs}
