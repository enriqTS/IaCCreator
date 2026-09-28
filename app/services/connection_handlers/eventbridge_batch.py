"""EventBridge submits a generated Batch job to the connected queue."""

from app.generators.hcl_renderer import Expr
from app.models.connection_configs.eventbridge_batch import EventBridgeBatchConfig
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.batch_task_target import prepare_batch_target
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
        target = self._find_instance(connection.target_name, project)
        prepare_batch_target(connection, project, target, config.job_definition_name)
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
