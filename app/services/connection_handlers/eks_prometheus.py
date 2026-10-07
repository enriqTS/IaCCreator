"""EKS modules own scrapers while destination modules retain workspace ownership."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.eks_prometheus import render_eks_scrapers
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.eks_prometheus import EksPrometheusConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class EksPrometheusHandler(BaseConnectionHandler):
    def _bindings(self, connection: ConnectionIR, project: ProjectIR) -> dict[str, int]:
        source = self._find_instance(connection.source_name, project)
        errors = []
        if source.config.authentication_mode == "CONFIG_MAP":
            errors.append(
                {
                    "loc": ("authentication_mode",),
                    "msg": "Managed collection requires API or API_AND_CONFIG_MAP authentication",
                }
            )
        if source.config.endpoint_private_access is False:
            errors.append(
                {
                    "loc": ("endpoint_private_access",),
                    "msg": "Managed collection requires private endpoint access",
                }
            )
        bindings = {}
        for item in project.connections:
            if (
                item.source_name != source.name
                or item.source_service != ServiceType.EKS
                or item.target_service != ServiceType.MANAGED_PROMETHEUS
                or item.connection_type != "sends_metrics"
            ):
                continue
            interval = EksPrometheusConfig.model_validate(
                item.connection_config
            ).scrape_interval_seconds
            if item.target_name in bindings and bindings[item.target_name] != interval:
                errors.append(
                    {
                        "loc": ("scrape_interval_seconds",),
                        "msg": "One EKS/workspace binding must use one scrape interval",
                    }
                )
            bindings[item.target_name] = interval
        if errors:
            raise InvalidConnectionConfigError(
                source.name, connection.target_name, connection.connection_type, errors
            )
        return dict(sorted(bindings.items()))

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        bindings = self._bindings(connection, project)
        name = connection.source_name
        source = self._find_instance(name, project)
        if source.config.authentication_mode is None:
            source.config.authentication_mode = "API_AND_CONFIG_MAP"
        if source.config.endpoint_private_access is None:
            source.config.endpoint_private_access = True
        values = {}
        for target, interval in bindings.items():
            self._find_instance(target, project).config._managed_scraper = True
            values[target] = {
                "workspace_arn": Expr(f"module.{target}.workspace_arn"),
                "scrape_interval_seconds": interval,
            }
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=name,
                    name="prometheus_scraper_workspaces",
                    type="map(object({ workspace_arn = string, scrape_interval_seconds = number }))",
                    value=self._renderer.render_expression(values),
                    description="Native Prometheus destinations and managed scrape intervals",
                )
            ],
            resources=[
                self._resource(
                    name,
                    "prometheus_scrapers.tf",
                    render_eks_scrapers(name, self._renderer),
                )
            ],
            outputs=[
                self._output(
                    name,
                    "prometheus_scrapers",
                    f"{{ for name, scraper in aws_prometheus_scraper.{name}_prometheus : name => {{ id = scraper.id, arn = scraper.arn, role_arn = scraper.role_arn, workspace_arn = scraper.destination[0].amp[0].workspace_arn }} }}",
                    "Managed scraper identities and AWS-owned service-linked roles keyed by workspace node name",
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
                message="Managed collection enables EKS API authentication and private endpoint access. Enabling API authentication cannot be reversed on an existing cluster; the default API_AND_CONFIG_MAP mode preserves existing aws-auth access. EKS and Prometheus must share an account and Region. The scraper uses all native cluster subnets (two to five), the cluster security group, and a VPC with DNS enabled. AWS creates its service-linked role and cluster access automatically; the deployment identity needs scraper, default-configuration, service-linked-role, and EKS access-management permissions. AWS's default scrape jobs require compatible metrics endpoints and workload annotations; workload metrics networking, node provisioning, dashboards, and alerts remain separately configured. Each binding creates a billed scraper subject to regional quotas; multiple scrapers are independent and do not configure deduplication.",
            )
        ]
