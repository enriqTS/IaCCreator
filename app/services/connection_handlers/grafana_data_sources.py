"""Data-source connections share a workspace-owned customer-managed IAM role."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.grafana_data_sources import render_grafana_role
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.grafana_cloudwatch import GrafanaCloudWatchSource
from app.services.connection_handlers.grafana_opensearch import GrafanaOpenSearchSource
from app.services.connection_handlers.grafana_prometheus import GrafanaPrometheusSource
from app.services.connection_handlers.grafana_source import GrafanaDataSource
from app.services.connection_handlers.grafana_timestream import GrafanaTimestreamSource


class GrafanaDataSourcesHandler(BaseConnectionHandler):
    def __init__(self) -> None:
        super().__init__()
        self._sources: tuple[GrafanaDataSource, ...] = (
            GrafanaPrometheusSource(),
            GrafanaCloudWatchSource(),
            GrafanaTimestreamSource(),
            GrafanaOpenSearchSource(),
        )

    def _check_workspace(self, connection: ConnectionIR, project: ProjectIR) -> None:
        source = self._find_instance(connection.source_name, project)
        if source.config.account_access_type != "CURRENT_ACCOUNT":
            raise InvalidConnectionConfigError(
                source.name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("account_access_type",),
                        "msg": "Managed data-source connections support current-account Grafana workspaces only; organization role chaining is not modeled",
                    }
                ],
            )

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        self._check_workspace(connection, project)
        name = connection.source_name
        source = self._find_instance(name, project)
        source.config._managed_data_sources = True
        source.config.permission_type = "CUSTOMER_MANAGED"
        result = ConnectionContribution()
        statements, preconditions = [], []
        for builder in self._sources:
            additions = builder.build(name, project)
            result.merge(additions.contribution)
            statements.extend(additions.statements)
            preconditions.extend(additions.preconditions)
        result.resources.append(
            self._resource(
                name,
                "data_source_role.tf",
                render_grafana_role(name, statements, preconditions, self._renderer),
            )
        )
        result.outputs.append(
            self._output(
                name,
                "data_source_role_arn",
                f"aws_iam_role.{name}_data_sources.arn",
                "IAM role for connected Grafana data sources",
            )
        )
        return result

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        self._check_workspace(connection, project)
        issues = [
            ConnectionIssue(
                severity="warning",
                message="The workspace uses a generated customer-managed role scoped to connected data sources. Apply the exported data-source settings through Grafana's data-source API or UI with an authorized Grafana identity; install the required plugins if needed. Other configured AWS data sources require their own grants. Identity Center/SAML setup, user access, metrics ingestion, dashboards, and private network connectivity remain separately configured.",
            )
        ]
        for builder in self._sources:
            issues.extend(builder.build(connection.source_name, project).issues)
        return issues
