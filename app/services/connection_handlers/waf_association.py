"""WAF associations for regional and CloudFront resources."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class WafLoadBalancerHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = safe_identifier(connection.target_name)
        content = self._renderer.render_resource(
            "aws_wafv2_web_acl_association",
            f"{target}_association",
            {
                "resource_arn": Expr(f"var.{target}_load_balancer_arn"),
                "web_acl_arn": Expr(f"aws_wafv2_web_acl.{connection.source_name}.arn"),
            },
        )
        return ConnectionContribution(
            inputs=[
                self._input(
                    connection.source_name,
                    connection.target_name,
                    "load_balancer_arn",
                    f"module.{connection.target_name}.load_balancer_arn",
                    "Protected load balancer ARN",
                )
            ],
            resources=[
                self._resource(
                    connection.source_name, f"association_{target}.tf", content
                )
            ],
        )


class WafCloudFrontHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = self._find_instance(connection.target_name, project)
        if target is not None:
            target.config.web_acl_id = "managed-by-connection"
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name="web_acl_id",
                    value=f"module.{connection.source_name}.web_acl_arn",
                    description="CloudFront Web ACL ARN",
                )
            ]
        )
