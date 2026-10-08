"""ECS owns one collector sidecar with workspace-scoped remote-write permissions."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.ecs_prometheus import render_collection_resources
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.ecs_prometheus import EcsPrometheusConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.network_placement import has_placement


class EcsPrometheusHandler(BaseConnectionHandler):
    def _bindings(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> tuple[list[str], EcsPrometheusConfig]:
        source = self._find_instance(connection.source_name, project)
        errors = []
        for field, service in (
            ("subnet_ids", ServiceType.SUBNET),
            ("security_group_ids", ServiceType.SECURITY_GROUP),
        ):
            if not has_placement(source.name, field, service, project):
                errors.append(
                    {
                        "loc": (field,),
                        "msg": "ECS collection requires subnet and security-group placement",
                    }
                )
        if source.config.ecs_launch_type not in {None, "FARGATE"}:
            errors.append(
                {
                    "loc": ("ecs_launch_type",),
                    "msg": "ECS collection supports the modeled Linux Fargate task",
                }
            )
        peers = [
            item
            for item in project.connections
            if item.source_name == source.name
            and item.source_service == ServiceType.ECS
            and item.target_service == ServiceType.MANAGED_PROMETHEUS
            and item.connection_type == "sends_metrics"
        ]
        configs = [
            EcsPrometheusConfig.model_validate(item.connection_config) for item in peers
        ]
        config = configs[0]
        if any(item != config for item in configs):
            errors.append(
                {
                    "loc": ("collection_interval_seconds",),
                    "msg": "One ECS task collector must share its interval and application metrics port across destinations",
                }
            )
        if errors:
            raise InvalidConnectionConfigError(
                source.name, connection.target_name, connection.connection_type, errors
            )
        return sorted({item.target_name for item in peers}), config

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        targets, config = self._bindings(connection, project)
        source = self._find_instance(connection.source_name, project)
        source.config._collects_prometheus = True
        source.config._requires_task_role = True
        source.config.ecs_launch_type = "FARGATE"
        values = {
            target: {
                "arn": Expr(f"module.{target}.workspace_arn"),
                "endpoint": Expr(f"module.{target}.prometheus_endpoint"),
                "region": Expr(f'split(":", module.{target}.workspace_arn)[3]'),
            }
            for target in targets
        }
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source.name,
                    name="prometheus_collection_workspaces",
                    type="map(object({ arn = string, endpoint = string, region = string }))",
                    value=self._renderer.render_expression(values),
                    description="Native Prometheus collection destinations",
                ),
                ModuleInput(
                    module=source.name,
                    name="prometheus_collection",
                    type="object({ collection_interval_seconds = number, application_metrics_port = number })",
                    value=self._renderer.render_expression(config.model_dump()),
                    description="Shared task metrics collection settings",
                ),
            ],
            outputs=[
                self._output(
                    source.name,
                    "prometheus_collector_configuration",
                    "local.prometheus_collector_configuration",
                    "ADOT configuration for task metrics and optional application scraping",
                ),
                self._output(
                    source.name,
                    "prometheus_collector_log_group",
                    f"aws_cloudwatch_log_group.{source.name}_prometheus.name",
                    "Collector diagnostic log group",
                ),
            ],
            resources=[
                self._resource(
                    source.name,
                    "prometheus_collection.tf",
                    render_collection_resources(source.name, self._renderer),
                )
            ],
            iam=[
                self._grant(
                    source.name,
                    IAMStatement(
                        actions=["aps:RemoteWrite"],
                        resources=[
                            f"${{aws_prometheus_workspace.{target}.arn}}"
                            for target in targets
                        ],
                    ),
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        self._bindings(connection, project)
        return [
            ConnectionIssue(
                severity="warning",
                message="Collection adds a nonessential ADOT v0.49.0 sidecar to each modeled Linux Fargate task, reserving 64 CPU units and 256 MiB. It collects metadata-v4 task/container metrics; optional application scraping requires a plain HTTP /metrics endpoint on the selected localhost port. Keep the reserved iac-prometheus-collector name out of application definitions. All destination bindings share one interval and application port. Task subnet/security-group placement, outbound access to Prometheus and the public collector image registry, application capacity, and long-running application containers are required. Existing application containers share the task role and its native workspace-scoped remote-write grants; logs and image pulls use the existing execution policy. Resource attributes become metric labels and increase ingestion/cardinality costs. Configure instrumentation, dashboards, alerts, and network rules separately; no cross-account destinations, task-wide discovery, or high-availability deduplication are configured.",
            )
        ]
