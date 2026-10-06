"""Selected LiveAnalytics tables contribute queries to the shared Grafana role."""

from app.generators.grafana_timestream import (
    timestream_data_sources_expression,
    timestream_query_statements,
    timestream_scope_preconditions,
)
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.table_access import TimestreamTableAccessConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.grafana_source import GrafanaSourceContribution


class GrafanaTimestreamSource(BaseConnectionHandler):
    def build(self, workspace: str, project: ProjectIR) -> GrafanaSourceContribution:
        bindings = sorted(
            {
                (
                    item.target_name,
                    TimestreamTableAccessConfig.model_validate(
                        item.connection_config
                    ).table_name,
                )
                for item in project.connections
                if item.source_name == workspace
                and item.source_service == ServiceType.MANAGED_GRAFANA
                and item.target_service == ServiceType.TIMESTREAM
                and item.connection_type == "queries"
            }
        )
        if not bindings:
            return GrafanaSourceContribution()
        values = {
            f"{target}:{table}": {
                "database_arn": Expr(f"module.{target}.database_arn"),
                "database_name": Expr(f"module.{target}.database_name"),
                "region": Expr(f"module.{target}.database_region"),
                "table_name": table,
            }
            for target, table in bindings
        }
        contribution = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=workspace,
                    name="timestream_tables",
                    type="map(object({ database_arn = string, database_name = string, region = string, table_name = string }))",
                    value=self._renderer.render_expression(values),
                    description="Native Timestream database identities and selected existing tables",
                )
            ],
            outputs=[
                ModuleOutput(
                    module=workspace,
                    name="timestream_data_sources",
                    value=str(timestream_data_sources_expression()),
                    description="Grafana Timestream data-source API payloads keyed by database node and table; apply these in Grafana",
                    depends_on=[
                        f"aws_grafana_workspace.{workspace}",
                        f"aws_iam_role_policy.{workspace}_data_sources",
                    ],
                ),
                *[
                    self._output(
                        target,
                        "database_region",
                        f'split(":", aws_timestreamwrite_database.{target}.arn)[3]',
                        "Native Timestream database Region",
                    )
                    for target in sorted({target for target, _ in bindings})
                ],
            ],
        )
        return GrafanaSourceContribution(
            contribution=contribution,
            statements=timestream_query_statements(),
            preconditions=timestream_scope_preconditions(),
            issues=[
                ConnectionIssue(
                    severity="warning",
                    message="Selected LiveAnalytics tables and their data must be provisioned separately. Queries are table-scoped, including multi-table queries only when every table is connected. Database/table discovery can reveal other names, and CancelQuery can cancel other queries in the connected Regions; these regional APIs and SELECT 1 health checks require wildcard resources. Install a compatible Timestream plugin and apply the exported settings in Grafana. LiveAnalytics is closed to new customers; use an eligible existing account. External encryption-key permissions and network connectivity remain separately configured.",
                )
            ],
        )
