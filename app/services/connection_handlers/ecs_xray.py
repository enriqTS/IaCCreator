"""ECS tracing owns one local exporter while groups own native membership."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.ecs_xray import OTLP_PORTS, render_xray_collection_resources
from app.models.connection_configs.ecs_prometheus import EcsPrometheusConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.ecs_collection import ecs_collection_errors
from app.services.connection_handlers.xray_group import (
    group_configuration_errors,
    group_membership_contribution,
)


class EcsXRayHandler(BaseConnectionHandler):
    def _validate_binding(self, connection: ConnectionIR, project: ProjectIR) -> None:
        errors = ecs_collection_errors(connection.source_name, project)
        target = self._find_instance(connection.target_name, project)
        errors.extend(group_configuration_errors(target.config))
        if any(
            EcsPrometheusConfig.model_validate(
                item.connection_config
            ).application_metrics_port
            in OTLP_PORTS
            for item in project.connections
            if item.source_name == connection.source_name
            and item.target_service == ServiceType.MANAGED_PROMETHEUS
            and item.connection_type == "sends_metrics"
        ):
            errors.append(
                {
                    "loc": ("application_metrics_port",),
                    "msg": "Prometheus application scraping must not use OTLP collector ports 4317 or 4318",
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
        peers = [
            item
            for item in project.connections
            if item.source_service == ServiceType.ECS
            and item.target_service == ServiceType.X_RAY
            and item.target_name == connection.target_name
            and item.connection_type == "traces_to"
        ]
        for item in peers:
            self._validate_binding(item, project)
        source = self._find_instance(connection.source_name, project)
        target = self._find_instance(connection.target_name, project)
        source.config._collects_xray = True
        source.config._requires_task_role = True
        source.config.ecs_launch_type = "FARGATE"
        target.config._managed_ecs_tracing = True
        result = group_membership_contribution(
            target.name,
            sorted({item.source_name for item in peers}),
            "xray_ecs_clusters",
            "cluster_arn",
            "xray_cluster_name",
        )
        result.resources.append(
            self._resource(
                source.name,
                "xray_collection.tf",
                render_xray_collection_resources(source.name, self._renderer),
            )
        )
        result.outputs.extend(
            [
                self._output(
                    source.name,
                    "xray_cluster_name",
                    f"aws_ecs_cluster.{source.name}.name",
                    "Native ECS trace group member name",
                ),
                self._output(
                    source.name,
                    "xray_collector_configuration",
                    "local.xray_collector_configuration",
                    "Task-local OTLP tracing collector configuration",
                ),
                self._output(
                    source.name,
                    "xray_collector_log_group",
                    f"aws_cloudwatch_log_group.{source.name}_xray.name",
                    "Tracing collector diagnostic log group",
                ),
            ]
        )
        return result

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        self._validate_binding(connection, project)
        return [
            ConnectionIssue(
                severity="warning",
                message="Tracing adds one nonessential ADOT v0.49.0 sidecar per Linux Fargate task, reserving 64 CPU units and 256 MiB, in addition to any Prometheus collector. OTLP listens only on task-local TCP ports 4317/4318; application definitions must leave them available. Application containers receive trace-only OTLP HTTP/protobuf environment settings; compatible application instrumentation, sampling, and trace-context propagation are still required. The collector stamps the native ECS cluster ARN as an indexed span annotation and uploads once to regional X-Ray, even with multiple groups. Groups combine producer selectors with the existing predicate using AND (the default keeps traces slower than five seconds); filters do not isolate readers or constrain ingestion. The shared task/execution role grants PutTraceSegments on wildcard resources in this Region; application containers share this permission. Diagnostic logs, public-image pulls, X-Ray API reachability, task capacity, nonzero service desired count, customer-managed X-Ray encryption, and tracing costs remain deployment concerns. Existing SDK sampling is preserved; no legacy UDP daemon, sampling proxy, or application instrumentation is installed.",
            )
        ]
