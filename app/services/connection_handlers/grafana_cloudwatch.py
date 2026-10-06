"""Connected log groups contribute read permissions to the shared Grafana role."""

from app.generators.grafana_cloudwatch import (
    cloudwatch_data_sources_expression,
    cloudwatch_query_statements,
    cloudwatch_scope_preconditions,
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
from app.services.connection_handlers.kms_references import managed_key


class GrafanaCloudWatchSource(BaseConnectionHandler):
    def build(self, workspace: str, project: ProjectIR) -> GrafanaSourceContribution:
        targets = sorted(
            {
                item.target_name
                for item in project.connections
                if item.source_name == workspace
                and item.source_service == ServiceType.MANAGED_GRAFANA
                and item.target_service == ServiceType.CLOUDWATCH
                and item.connection_type == "queries"
            }
        )
        if not targets:
            return GrafanaSourceContribution()
        values = {
            target: {
                "arn": Expr(f"module.{target}.log_group_arn"),
                "name": Expr(f"module.{target}.log_group_name"),
                "region": Expr(f"module.{target}.log_group_region"),
                "kms_key_arn": Expr(f"module.{target}.log_group_kms_key_arn"),
                "log_group_class": Expr(f"module.{target}.log_group_class"),
            }
            for target in targets
        }
        outputs = [
            ModuleOutput(
                module=workspace,
                name="cloudwatch_data_sources",
                value=str(cloudwatch_data_sources_expression()),
                description="Grafana CloudWatch Logs data-source API payloads keyed by native Region; apply these in Grafana",
                depends_on=[
                    f"aws_grafana_workspace.{workspace}",
                    f"aws_iam_role_policy.{workspace}_data_sources",
                ],
            )
        ]
        for target in targets:
            ref = f"aws_cloudwatch_log_group.{target}"
            for name, value in {
                "log_group_name": f"{ref}.name",
                "log_group_region": f'split(":", {ref}.arn)[3]',
                "log_group_kms_key_arn": f'{ref}.kms_key_id == null ? "" : {ref}.kms_key_id',
                "log_group_class": f"{ref}.log_group_class",
            }.items():
                outputs.append(
                    self._output(
                        target, name, value, "Native CloudWatch log-group metadata"
                    )
                )
        issues = [
            ConnectionIssue(
                severity="warning",
                message="CloudWatch access covers Logs Insights queries and event reads for connected log groups. Regional log-group discovery and cancellation require wildcard resources; StopQuery can cancel other queries in those Regions. CloudWatch metrics, tag/Region discovery, log-data-source selectors, and metrics health checks require separate grants. Use the Logs query mode with the exported default groups.",
            )
        ]
        if any(
            self._find_instance(target, project).config.kms_key_id
            and not managed_key(target, project)
            for target in targets
        ):
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="The external KMS key owner must permit the regional CloudWatch Logs service and the Grafana role to decrypt the connected group's data. Historical keys and account-level query-result encryption keys need separate permissions.",
                )
            )
        return GrafanaSourceContribution(
            contribution=ConnectionContribution(
                inputs=[
                    ModuleInput(
                        module=workspace,
                        name="cloudwatch_log_groups",
                        type="map(object({ arn = string, name = string, region = string, kms_key_arn = string, log_group_class = string }))",
                        value=self._renderer.render_expression(values),
                        description="Native CloudWatch log-group identities and encryption metadata",
                    )
                ],
                outputs=outputs,
            ),
            statements=cloudwatch_query_statements(),
            preconditions=cloudwatch_scope_preconditions(),
            issues=issues,
        )
