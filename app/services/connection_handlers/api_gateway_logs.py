"""HTTP logging passes managed destinations to stage rendering without account ownership."""

from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.api_gateway_logs_bindings import (
    resolve_api_access_logs,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_external_policy import (
    external_service_key_issues,
)


class ApiGatewayLogsHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        bindings = resolve_api_access_logs(connection.source_name, project)
        peers = [
            item
            for item in project.connections
            if item.source_name == connection.source_name
            and item.source_service == ServiceType.API_GATEWAY
            and item.target_service == ServiceType.CLOUDWATCH
            and item.connection_type == "logs_to"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        config = self._find_instance(connection.source_name, project).config
        config._managed_access_log_stages = {binding.stage_name for binding in bindings}
        if config.stages is None:
            config.stages = []
        values = {
            binding.stage_name: {
                "arn": Expr(f"module.{binding.log_group_name}.log_group_arn"),
                "format": binding.log_format.replace("${", "$${").replace("%{", "%%{"),
            }
            for binding in bindings
        }
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.source_name,
                    name="api_access_logs",
                    type="map(object({ arn = string, format = string }))",
                    value=self._renderer.render_expression(values),
                    description="Managed HTTP access-log settings by stage",
                )
            ],
            resources=[
                self._resource(
                    connection.source_name,
                    "access_logs.tf",
                    'data "aws_partition" "api_access_logs" {}\n\ndata "aws_region" "api_access_logs" {}\n\ndata "aws_caller_identity" "api_access_logs" {}\n',
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_api_access_logs(connection.source_name, project)
        return [
            *external_service_key_issues(connection, project),
            ConnectionIssue(
                severity="warning",
                message="The selected HTTP API stage writes access logs to the connected group. AWS owns HTTP log delivery and its resource policy; the Terraform deployment identity needs CloudWatch log-delivery and resource-policy permissions. Account policy size and delivery limits remain operational prerequisites. This connection does not configure WebSocket account logging, execution logs, tracing, or application instrumentation. Existing deployment settings are preserved; a named stage without automatic deployment still needs a deployment. Log retention and encryption belong to the connected group; external keys must authorize the regional CloudWatch Logs service. Custom formats can include sensitive request metadata; access logs incur storage and ingestion costs.",
            ),
        ]
