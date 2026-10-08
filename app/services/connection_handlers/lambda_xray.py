"""Active Lambda tracing supplies native X-Ray group selectors."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.lambda_xray import render_lambda_xray_policy
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.xray_group import (
    group_configuration_errors,
    group_membership_contribution,
)


class LambdaXRayHandler(BaseConnectionHandler):
    def _validate_binding(self, connection: ConnectionIR, project: ProjectIR) -> None:
        function = self._find_instance(connection.source_name, project).config
        group = self._find_instance(connection.target_name, project).config
        errors = group_configuration_errors(group)
        if function.is_layer:
            errors.append(
                {"loc": ("is_layer",), "msg": "Lambda layers cannot emit traces"}
            )
        if function.tracing_mode not in {None, "Active"}:
            errors.append(
                {
                    "loc": ("tracing_mode",),
                    "msg": "This connection requires Active tracing",
                }
            )
        if errors:
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                errors,
            )

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        members = sorted(
            {
                item.source_name
                for item in project.connections
                if item.source_service == ServiceType.LAMBDA
                and item.target_service == ServiceType.X_RAY
                and item.target_name == connection.target_name
                and item.connection_type == "traces_to"
            }
        )
        for item in project.connections:
            if (
                item.source_name in members
                and item.target_name == connection.target_name
            ):
                self._validate_binding(item, project)
        source = self._find_instance(connection.source_name, project)
        target = self._find_instance(connection.target_name, project)
        source.config.tracing_mode = "Active"
        source.config._managed_xray = True
        target.config._managed_lambda_tracing = True
        result = group_membership_contribution(
            target.name,
            members,
            "xray_lambda_functions",
            "function_arn",
            "function_name",
        )
        result.resources.append(
            self._resource(
                source.name,
                "xray_tracing.tf",
                render_lambda_xray_policy(source.name, self._renderer),
            )
        )
        return result

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        self._validate_binding(connection, project)
        return [
            ConnectionIssue(
                severity="warning",
                message="This connection enables Active Lambda tracing and grants PutTraceSegments/PutTelemetryRecords on wildcard resources in the function's Region. X-Ray groups select traces; filters do not restrict upload permissions or isolate readers. Both Lambda service and function segments are selected by native name/account, combined with the existing group filter using AND (the default keeps only traces slower than five seconds). Lambda uses managed sampling; this connection does not install application instrumentation or change published versions/alias routing. Kafka/MSK, MQ, and DocumentDB event-source tracing is unsupported. Custom spans, downstream context propagation, private-network API access, customer-managed X-Ray encryption, and costs remain deployment concerns.",
            )
        ]
