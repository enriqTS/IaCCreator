"""Active Lambda tracing supplies native X-Ray group selectors."""

import re

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.generators.lambda_xray import render_lambda_xray_policy
from app.generators.xray_filters import (
    XRAY_GROUP_NAME_PATTERN,
    render_xray_scope_data,
)
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class LambdaXRayHandler(BaseConnectionHandler):
    def _validate_binding(self, connection: ConnectionIR, project: ProjectIR) -> None:
        function = self._find_instance(connection.source_name, project).config
        group = self._find_instance(connection.target_name, project).config
        errors = []
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
        if (
            not re.fullmatch(XRAY_GROUP_NAME_PATTERN, group.group_name)
            or group.group_name == "Default"
        ):
            errors.append(
                {
                    "loc": ("group_name",),
                    "msg": "Use a concrete non-reserved X-Ray group name",
                }
            )
        if not group.filter_expression.strip():
            errors.append(
                {
                    "loc": ("filter_expression",),
                    "msg": "The additional group filter must be nonempty",
                }
            )
        if group.notifications_enabled and not group.insights_enabled:
            errors.append(
                {
                    "loc": ("notifications_enabled",),
                    "msg": "Insights notifications require Insights",
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
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=target.name,
                    name="xray_lambda_functions",
                    type="map(object({ arn = string, name = string }))",
                    value=self._renderer.render_expression(
                        {
                            name: {
                                "arn": Expr(f"module.{name}.function_arn"),
                                "name": Expr(f"module.{name}.function_name"),
                            }
                            for name in members
                        }
                    ),
                    description="Native Lambda identities selecting traces for this X-Ray group",
                )
            ],
            resources=[
                self._resource(
                    source.name,
                    "xray_tracing.tf",
                    render_lambda_xray_policy(source.name, self._renderer),
                ),
                self._resource(
                    target.name, "xray_tracing.tf", render_xray_scope_data()
                ),
            ],
            outputs=[
                self._output(
                    target.name,
                    "trace_filter_expression",
                    f"aws_xray_group.{target.name}.filter_expression",
                    "Effective native trace filter including connected Lambda functions",
                )
            ],
        )

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
