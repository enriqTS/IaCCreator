"""Native log destinations reuse the ECS execution role and log-group encryption."""

from app.generators.ecs_logs import render_ecs_log_resources
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.ecs_logs_bindings import resolve_ecs_logs
from app.services.connection_handlers.ecs_logs_encryption import ecs_log_encryption
from app.services.connection_handlers.kms_external_policy import (
    external_service_key_issues,
)


class EcsLogsHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        bindings = resolve_ecs_logs(connection.source_name, project)
        peers = [
            item
            for item in project.connections
            if item.source_name == connection.source_name
            and item.source_service == ServiceType.ECS
            and item.target_service == ServiceType.CLOUDWATCH
            and item.connection_type == "logs_to"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        source = self._find_instance(connection.source_name, project)
        source.config._application_logs = True
        source.config.ecs_launch_type = "FARGATE"
        values = {
            binding.container_name: {
                "arn": Expr(f"module.{binding.log_group}.log_group_arn"),
                "stream_prefix": binding.stream_prefix,
                "mode": binding.mode,
                "buffer_size_mib": binding.buffer_size_mib,
            }
            for binding in bindings
        }
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source.name,
                    name="ecs_logs",
                    type="map(object({ arn = string, stream_prefix = string, mode = string, buffer_size_mib = number }))",
                    value=self._renderer.render_expression(values),
                    description="Managed application log destinations and delivery settings keyed by container",
                )
            ],
            resources=[
                self._resource(
                    source.name, "application_logs.tf", render_ecs_log_resources()
                )
            ],
            outputs=[
                self._output(
                    source.name,
                    "application_log_configurations",
                    "local.application_log_configurations",
                    "Native application log driver settings keyed by container",
                )
            ],
        )
        encryption = ecs_log_encryption(source.name, bindings, project, self._renderer)
        source.config._application_logs_kms = any(
            item.filename == "application_log_encryption.tf"
            for item in encryption.resources
        )
        result.merge(encryption)
        return result

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_ecs_logs(connection.source_name, project)
        return [
            *external_service_key_issues(connection, project),
            ConnectionIssue(
                severity="warning",
                message="The selected application container sends stdout/stderr through awslogs to the managed group. Supply a matching container without manual logConfiguration in container_definitions. The ECS-owned execution role is attached and retains its existing wildcard image-pull and log-write permissions; application credentials share that role only when other connections attach it as a task role. Non-blocking delivery uses a task-memory buffer and can drop logs when full; blocking delivery can stall application output during delivery failures. Task memory must cover application reservations, collectors, and managed buffers. Retention and encryption belong to the connected log group; CloudWatch Logs performs encryption, and the execution role receives key-scoped permissions constrained to the regional Logs service and group encryption context; external key policies must authorize both the Logs service and execution role. Provide real images, nonzero desired count, network access to Logs/image registries, and suitable costs/capacity. Existing application settings and collector diagnostic destinations remain separate; application log files, FireLens, multiline parsing, log group auto-creation, and direct application KMS use are not configured.",
            ),
        ]
