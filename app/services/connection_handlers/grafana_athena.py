"""Athena table bindings contribute to the shared Grafana data-source role."""

from app.generators.grafana_athena import (
    athena_data_sources_expression,
    athena_query_statements,
    athena_scope_preconditions,
)
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.grafana_athena import GrafanaAthenaConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.athena_results import validate_athena_results
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.grafana_source import GrafanaSourceContribution


class GrafanaAthenaSource(BaseConnectionHandler):
    def build(self, workspace: str, project: ProjectIR) -> GrafanaSourceContribution:
        bindings = sorted(
            {
                (item.target_name, config.database_name, config.table_name)
                for item in project.connections
                if item.source_name == workspace
                and item.source_service == ServiceType.MANAGED_GRAFANA
                and item.target_service == ServiceType.ATHENA
                and item.connection_type == "queries"
                for config in [
                    GrafanaAthenaConfig.model_validate(item.connection_config)
                ]
            }
        )
        if not bindings:
            return GrafanaSourceContribution()
        targets = sorted({target for target, _, _ in bindings})
        for target in targets:
            validate_athena_results(
                workspace, self._find_instance(target, project), project
            )
        values = {
            f"{target}:{database}:{table}": {
                "arn": Expr(f"module.{target}.workgroup_arn"),
                "workgroup_name": Expr(f"module.{target}.workgroup_name"),
                "region": Expr(f"module.{target}.grafana_workgroup_region"),
                "output_location": Expr(f"module.{target}.grafana_result_location"),
                "enforce_configuration": Expr(
                    f"module.{target}.grafana_enforce_configuration"
                ),
                "database_name": database,
                "table_name": table,
            }
            for target, database, table in bindings
        }
        outputs = [
            ModuleOutput(
                module=workspace,
                name="athena_data_sources",
                value=str(athena_data_sources_expression()),
                description="Grafana Athena API payloads keyed by workgroup node and database; apply these in Grafana",
                depends_on=[
                    f"aws_grafana_workspace.{workspace}",
                    f"aws_iam_role_policy.{workspace}_data_sources",
                ],
            )
        ]
        for target in targets:
            ref = f"aws_athena_workgroup.{target}"
            for name, value in {
                "grafana_workgroup_region": f'split(":", {ref}.arn)[3]',
                "grafana_result_location": f'try({ref}.configuration[0].result_configuration[0].output_location, "")',
                "grafana_enforce_configuration": f"{ref}.configuration[0].enforce_workgroup_configuration",
            }.items():
                outputs.append(
                    self._output(
                        target, name, value, "Native Athena workgroup result metadata"
                    )
                )
        return GrafanaSourceContribution(
            contribution=ConnectionContribution(
                inputs=[
                    ModuleInput(
                        module=workspace,
                        name="athena_tables",
                        type="map(object({ arn = string, workgroup_name = string, region = string, output_location = string, enforce_configuration = bool, database_name = string, table_name = string }))",
                        value=self._renderer.render_expression(values),
                        description="Native Athena workgroups and selected existing Glue tables",
                    )
                ],
                outputs=outputs,
            ),
            statements=athena_query_statements(),
            preconditions=athena_scope_preconditions(),
            issues=[
                ConnectionIssue(
                    severity="warning",
                    message="Athena execution, query-result reads, and cancellation cover each connected workgroup, including other users' queries. Result-object read/write permissions cover its enforced S3 prefix; bucket listings can reveal other key names. Glue metadata access selects existing AwsDataCatalog tables and ancestors, but SQL text is not restricted to SELECT by IAM. Dataset S3 access, catalog/result/data KMS permissions, Lake Formation grants, and network access remain external; use a dedicated result prefix and supply those permissions separately. Provision catalog tables and data, install a compatible Athena plugin, and apply the exported Grafana settings. Custom/federated catalogs, managed query-result storage, and trusted identity propagation are not modeled.",
                )
            ],
        )
