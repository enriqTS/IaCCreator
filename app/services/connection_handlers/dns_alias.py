"""Route 53 aliases owned by hosted-zone modules."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class DnsAliasHandler(BaseConnectionHandler):
    def __init__(
        self,
        dns_output: str,
        zone_output: str,
    ) -> None:
        super().__init__()
        self._dns_output = dns_output
        self._zone_output = zone_output

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = safe_identifier(connection.target_name)
        dns_variable = f"{target}_alias_dns_name"
        zone_variable = f"{target}_alias_zone_id"
        config = connection.connection_config
        content = self._renderer.render_resource(
            "aws_route53_record",
            f"{target}_alias",
            {
                "zone_id": Expr(f"aws_route53_zone.{connection.source_name}.zone_id"),
                "name": config.get("record_name", ""),
                "type": "A",
                "alias": {
                    "name": Expr(f"var.{dns_variable}"),
                    "zone_id": Expr(f"var.{zone_variable}"),
                    "evaluate_target_health": config.get(
                        "evaluate_target_health", False
                    ),
                },
            },
        )
        return ConnectionContribution(
            inputs=[
                self._input(
                    connection.source_name,
                    connection.target_name,
                    "alias_dns_name",
                    f"module.{connection.target_name}.{self._dns_output}",
                    "DNS name of the alias target",
                ),
                self._input(
                    connection.source_name,
                    connection.target_name,
                    "alias_zone_id",
                    f"module.{connection.target_name}.{self._zone_output}",
                    "Hosted zone ID of the alias target",
                ),
            ],
            resources=[
                self._resource(
                    connection.source_name,
                    f"alias_{target}.tf",
                    content,
                )
            ],
        )
