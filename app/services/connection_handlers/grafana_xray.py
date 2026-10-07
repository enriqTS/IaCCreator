"""X-Ray groups contribute regional readers and native query templates."""

import re

from app.exceptions import InvalidConnectionConfigError
from app.generators.grafana_xray import (
    XRAY_GROUP_NAME_PATTERN,
    xray_data_sources_expression,
    xray_query_defaults_expression,
    xray_query_statements,
    xray_scope_preconditions,
)
from app.generators.hcl_renderer import Expr
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


class GrafanaXRaySource(BaseConnectionHandler):
    def build(self, workspace: str, project: ProjectIR) -> GrafanaSourceContribution:
        targets = sorted(
            {
                item.target_name
                for item in project.connections
                if item.source_name == workspace
                and item.source_service == ServiceType.MANAGED_GRAFANA
                and item.target_service == ServiceType.X_RAY
                and item.connection_type == "queries"
            }
        )
        if not targets:
            return GrafanaSourceContribution()
        for target in targets:
            config = self._find_instance(target, project).config
            errors = []
            if (
                not re.fullmatch(XRAY_GROUP_NAME_PATTERN, config.group_name)
                or config.group_name == "Default"
            ):
                errors.append(
                    {
                        "loc": ("group_name",),
                        "msg": "Grafana requires a concrete non-reserved X-Ray group name with up to 32 ASCII letters, digits, underscores, or hyphens",
                    }
                )
            if not config.filter_expression.strip():
                errors.append(
                    {
                        "loc": ("filter_expression",),
                        "msg": "Grafana requires a nonempty X-Ray group query filter",
                    }
                )
            if errors:
                raise InvalidConnectionConfigError(workspace, target, "queries", errors)
        values = {
            target: {
                "arn": Expr(f"module.{target}.group_arn"),
                "name": Expr(f"module.{target}.group_name"),
                "region": Expr(f"module.{target}.grafana_group_region"),
                "filter_expression": Expr(f"module.{target}.grafana_group_filter"),
                "insights_enabled": Expr(
                    f"module.{target}.grafana_group_insights_enabled"
                ),
            }
            for target in targets
        }
        outputs = [
            ModuleOutput(
                module=workspace,
                name=name,
                value=str(expression),
                description=description,
                depends_on=[
                    f"aws_grafana_workspace.{workspace}",
                    f"aws_iam_role_policy.{workspace}_data_sources",
                ],
            )
            for name, expression, description in [
                (
                    "xray_data_sources",
                    xray_data_sources_expression(),
                    "Regional Grafana X-Ray data-source API payloads; apply these in Grafana",
                ),
                (
                    "xray_query_defaults",
                    xray_query_defaults_expression(),
                    "Native X-Ray group query defaults keyed by node name; apply these to Grafana queries",
                ),
            ]
        ]
        for target in targets:
            ref = f"aws_xray_group.{target}"
            for name, value in {
                "grafana_group_region": f'split(":", {ref}.arn)[3]',
                "grafana_group_filter": f"{ref}.filter_expression",
                "grafana_group_insights_enabled": f"try({ref}.insights_configuration[0].insights_enabled, false)",
            }.items():
                outputs.append(
                    self._output(target, name, value, "Native X-Ray group metadata")
                )
        return GrafanaSourceContribution(
            contribution=ConnectionContribution(
                inputs=[
                    ModuleInput(
                        module=workspace,
                        name="xray_groups",
                        type="map(object({ arn = string, name = string, region = string, filter_expression = string, insights_enabled = bool }))",
                        value=self._renderer.render_expression(values),
                        description="Native X-Ray group identities, query filters, and Insights settings",
                    )
                ],
                outputs=outputs,
            ),
            statements=xray_query_statements(),
            preconditions=xray_scope_preconditions(),
            issues=[
                ConnectionIssue(
                    severity="warning",
                    message="X-Ray trace, graph, statistics, and group discovery APIs require wildcard resources and allow reading unrelated traces and groups in connected Regions. Native group filters are query defaults, not IAM authorization boundaries. Insights reads are enabled in Regions containing a connected Insights-enabled group and also cover unrelated insights. EC2 Region discovery supports older plugin versions and can reveal other Region names. Install a compatible X-Ray plugin and apply the exported data-source and query settings; newer versions may call it AWS Application Signals. Use X-Ray query mode; Application Signals, cross-account OAM, and CloudWatch Transaction Search permissions are not generated. Application instrumentation, trace ingestion, sampling, dashboards, Grafana user isolation, encryption grants, and AWS API network access remain separately configured.",
                )
            ],
        )
