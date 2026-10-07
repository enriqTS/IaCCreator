"""Provisioned Redshift bindings contribute to the shared Grafana role."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.grafana_redshift import (
    redshift_data_sources_expression,
    redshift_query_statements,
    redshift_scope_preconditions,
)
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.grafana_redshift import GrafanaRedshiftConfig
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


class GrafanaRedshiftSource(BaseConnectionHandler):
    def build(self, workspace: str, project: ProjectIR) -> GrafanaSourceContribution:
        bindings = sorted(
            {
                (item.target_name, config.database_name, config.database_user)
                for item in project.connections
                if item.source_name == workspace
                and item.source_service == ServiceType.MANAGED_GRAFANA
                and item.target_service == ServiceType.REDSHIFT
                and item.connection_type == "queries"
                for config in [
                    GrafanaRedshiftConfig.model_validate(item.connection_config)
                ]
            }
        )
        if not bindings:
            return GrafanaSourceContribution()
        for target, _, user in bindings:
            config = self._find_instance(target, project).config
            missing = [
                field
                for field in ("node_type", "master_username")
                if not getattr(config, field)
            ]
            if missing or user in {"public", (config.master_username or "").lower()}:
                raise InvalidConnectionConfigError(
                    workspace,
                    target,
                    "queries",
                    [
                        {
                            "loc": tuple(missing) if missing else ("database_user",),
                            "msg": "Redshift requires node_type, master_username, and an existing non-administrator database user",
                        }
                    ],
                )
            config._grafana_query_access = True
        values = {
            f"{target}:{database}:{user}": {
                "arn": Expr(f"module.{target}.cluster_arn"),
                "cluster_identifier": Expr(
                    f"module.{target}.grafana_cluster_identifier"
                ),
                "region": Expr(f"module.{target}.grafana_cluster_region"),
                "master_username": Expr(f"module.{target}.grafana_master_username"),
                "database_name": database,
                "database_user": user,
            }
            for target, database, user in bindings
        }
        outputs = [
            ModuleOutput(
                module=workspace,
                name="redshift_data_sources",
                value=str(redshift_data_sources_expression()),
                description="Grafana Redshift API payloads keyed by cluster node, database, and user; apply these in Grafana",
                depends_on=[
                    f"aws_grafana_workspace.{workspace}",
                    f"aws_iam_role_policy.{workspace}_data_sources",
                ],
            )
        ]
        for target in sorted({target for target, _, _ in bindings}):
            ref = f"aws_redshift_cluster.{target}"
            for name, value in {
                "grafana_cluster_identifier": f"{ref}.cluster_identifier",
                "grafana_cluster_region": f'split(":", {ref}.arn)[3]',
                "grafana_master_username": f"{ref}.master_username",
            }.items():
                outputs.append(
                    self._output(
                        target, name, value, "Native Redshift cluster metadata"
                    )
                )
        return GrafanaSourceContribution(
            contribution=ConnectionContribution(
                inputs=[
                    ModuleInput(
                        module=workspace,
                        name="redshift_databases",
                        type="map(object({ arn = string, cluster_identifier = string, region = string, master_username = string, database_name = string, database_user = string }))",
                        value=self._renderer.render_expression(values),
                        description="Native Redshift cluster identities and selected existing database/user pairs",
                    )
                ],
                outputs=outputs,
            ),
            statements=redshift_query_statements(),
            preconditions=redshift_scope_preconditions(),
            issues=[
                ConnectionIssue(
                    severity="warning",
                    message="Provision the selected databases and existing non-administrator users with read-only SQL grants separately; IAM does not restrict SQL to SELECT or verify that a user lacks superuser privileges. Connected clusters use an AWS-managed administrator password, requiring deployment permissions for Secrets Manager. Use a Data API eligible node type, appropriate capacity, and VPC placement. Query metadata may reveal other database/schema/table names. Statement results, status, listing, and cancellation require regional wildcard permissions and share the workspace role's statements across its sessions and Grafana users. Install a compatible Redshift plugin and apply the exported settings. AWS API egress, endpoint policies, encryption grants, and database lifecycle remain external; Serverless and secret-based data-source authentication are not modeled.",
                )
            ],
        )
