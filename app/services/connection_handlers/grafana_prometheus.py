"""Connected Prometheus workspaces supply scoped queries and Grafana API payloads."""

from app.generators.grafana_prometheus import (
    prometheus_data_sources_expression,
    prometheus_scope_preconditions,
)
from app.generators.hcl_renderer import Expr
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.grafana_source import GrafanaSourceContribution


class GrafanaPrometheusSource(BaseConnectionHandler):
    def build(self, workspace: str, project: ProjectIR) -> GrafanaSourceContribution:
        targets = sorted(
            {
                item.target_name
                for item in project.connections
                if item.source_name == workspace
                and item.source_service == ServiceType.MANAGED_GRAFANA
                and item.target_service == ServiceType.MANAGED_PROMETHEUS
                and item.connection_type == "queries"
            }
        )
        if not targets:
            return GrafanaSourceContribution()
        values = {
            target: {
                "arn": Expr(f"module.{target}.workspace_arn"),
                "endpoint": Expr(f"module.{target}.prometheus_endpoint"),
                "region": Expr(f"module.{target}.workspace_region"),
            }
            for target in targets
        }
        contribution = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=workspace,
                    name="prometheus_workspaces",
                    type="map(object({ arn = string, endpoint = string, region = string }))",
                    value=self._renderer.render_expression(values),
                    description="Managed Prometheus identities and endpoints",
                )
            ],
            outputs=[
                ModuleOutput(
                    module=workspace,
                    name="prometheus_data_sources",
                    value=str(prometheus_data_sources_expression()),
                    description="Grafana data-source API payloads keyed by diagram resource name; apply these in Grafana after workspace creation",
                    depends_on=[
                        f"aws_grafana_workspace.{workspace}",
                        f"aws_iam_role_policy.{workspace}_data_sources",
                    ],
                ),
                *[
                    self._output(
                        target,
                        "workspace_region",
                        f'split(":", aws_prometheus_workspace.{target}.arn)[3]',
                        "Native Prometheus workspace Region",
                    )
                    for target in targets
                ],
            ],
        )
        return GrafanaSourceContribution(
            contribution=contribution,
            statements=[
                {
                    "Effect": "Allow",
                    "Action": [
                        "aps:QueryMetrics",
                        "aps:GetLabels",
                        "aps:GetSeries",
                        "aps:GetMetricMetadata",
                    ],
                    "Resource": Expr(
                        "[for workspace in values(var.prometheus_workspaces) : workspace.arn]"
                    ),
                }
            ],
            preconditions=prometheus_scope_preconditions(),
        )
