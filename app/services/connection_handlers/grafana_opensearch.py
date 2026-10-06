"""OpenSearch domains contribute native metadata and read-only multi-search access."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.grafana_opensearch import (
    opensearch_data_sources_expression,
    opensearch_query_statements,
    opensearch_scope_preconditions,
)
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.grafana_opensearch import GrafanaOpenSearchConfig
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


class GrafanaOpenSearchSource(BaseConnectionHandler):
    def build(self, workspace: str, project: ProjectIR) -> GrafanaSourceContribution:
        bindings = {}
        for item in project.connections:
            if (
                item.source_name != workspace
                or item.source_service != ServiceType.MANAGED_GRAFANA
                or item.target_service != ServiceType.OPENSEARCH
                or item.connection_type != "queries"
            ):
                continue
            config = GrafanaOpenSearchConfig.model_validate(item.connection_config)
            key = (item.target_name, config.index_name)
            if key in bindings and bindings[key] != config:
                self._reject(
                    workspace,
                    item.target_name,
                    "time_field",
                    "A Grafana domain/index binding has conflicting time-field defaults",
                )
            bindings[key] = config
        if not bindings:
            return GrafanaSourceContribution()
        targets = sorted({target for target, _ in bindings})
        for target in targets:
            if any(
                item.target_name == target
                and item.target_service == ServiceType.OPENSEARCH
                and item.connection_type in {"reads_from", "writes_to", "resolves_with"}
                for item in project.connections
            ):
                self._reject(
                    workspace,
                    target,
                    "index_name",
                    "Grafana root multi-search requires explicit request-body indexes, which conflict with index-scoped Lambda/ECS/AppSync clients on this domain; use separate domains",
                )
        values = {
            f"{target}:{index}": {
                "arn": Expr(f"module.{target}.domain_arn"),
                "endpoint": Expr(f"module.{target}.domain_endpoint"),
                "domain_name": Expr(f"module.{target}.grafana_domain_name"),
                "region": Expr(f"module.{target}.grafana_domain_region"),
                "engine_version": Expr(f"module.{target}.grafana_engine_version"),
                "allow_explicit_index": Expr(f"module.{target}.grafana_explicit_index"),
                "index_name": index,
                "time_field": config.time_field,
            }
            for (target, index), config in sorted(bindings.items())
        }
        outputs = [
            ModuleOutput(
                module=workspace,
                name="opensearch_data_sources",
                value=str(opensearch_data_sources_expression()),
                description="Grafana OpenSearch API payloads keyed by domain node and default index; apply these in Grafana",
                depends_on=[
                    f"aws_grafana_workspace.{workspace}",
                    f"aws_iam_role_policy.{workspace}_data_sources",
                ],
            )
        ]
        for target in targets:
            self._find_instance(target, project).config._grafana_query_access = True
            ref = f"aws_opensearch_domain.{target}"
            for name, value in {
                "grafana_domain_name": f"{ref}.domain_name",
                "grafana_domain_region": f'split(":", {ref}.arn)[3]',
                "grafana_engine_version": f"{ref}.engine_version",
                "grafana_explicit_index": f'lookup({ref}.advanced_options, "rest.action.multi.allow_explicit_index", "true")',
            }.items():
                outputs.append(
                    self._output(
                        target,
                        name,
                        value,
                        "Native OpenSearch metadata for Grafana queries",
                    )
                )
        return GrafanaSourceContribution(
            contribution=ConnectionContribution(
                inputs=[
                    ModuleInput(
                        module=workspace,
                        name="opensearch_sources",
                        type="map(object({ arn = string, endpoint = string, domain_name = string, region = string, engine_version = string, allow_explicit_index = string, index_name = string, time_field = string }))",
                        value=self._renderer.render_expression(values),
                        description="Native OpenSearch domains and Grafana query defaults",
                    )
                ],
                outputs=outputs,
            ),
            statements=opensearch_query_statements(),
            preconditions=opensearch_scope_preconditions(),
            issues=[
                ConnectionIssue(
                    severity="warning",
                    message="Grafana multi-search can read any index in each connected domain; the selected index is a default, not an IAM boundary. Only version discovery, configured-index metadata, and root multi-search are granted. The domain enables explicit request-body indexes and HTTPS; index-scoped Lambda/ECS/AppSync clients on the same domain are incompatible. Provision indexes/date mappings separately. Domain policies, fine-grained security role mappings, and network reachability remain external and can broaden or deny access. Install a compatible plugin and apply the exported settings; PPL, SQL, cluster administration, and document mutations are excluded.",
                )
            ],
        )

    @staticmethod
    def _reject(workspace: str, target: str, field: str, message: str) -> None:
        raise InvalidConnectionConfigError(
            workspace, target, "queries", [{"loc": (field,), "msg": message}]
        )
