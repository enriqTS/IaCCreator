"""ALB-owned confidential clients for Cognito browser authentication."""

from app.generators.hcl_renderer import Expr
from app.models.connection_configs.cognito_load_balancer import (
    CognitoLoadBalancerConfig,
)
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.cognito_load_balancer_bindings import (
    resolve_cognito_listener_bindings,
)


class CognitoLoadBalancerHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        bindings = resolve_cognito_listener_bindings(connection.target_name, project)
        config = CognitoLoadBalancerConfig.model_validate(connection.connection_config)
        binding = bindings[config.listener_port]
        prefix = f"cognito_{binding.pool_name}"
        content = self._renderer.render_resource(
            "aws_cognito_user_pool_client",
            binding.client_resource,
            {
                "name": binding.client_resource,
                "user_pool_id": Expr(f"var.{prefix}_user_pool_id"),
                "generate_secret": True,
                "allowed_oauth_flows_user_pool_client": True,
                "allowed_oauth_flows": ["code"],
                "allowed_oauth_scopes": binding.config.scopes.split(),
                "callback_urls": [binding.callback_url],
                "supported_identity_providers": ["COGNITO"],
                "prevent_user_existence_errors": "ENABLED",
                "enable_token_revocation": True,
                "lifecycle": {
                    "precondition": {
                        "condition": Expr(
                            f'split(":", var.{prefix}_user_pool_arn)[3] == split(":", aws_lb.{connection.target_name}.arn)[3]'
                        ),
                        "error_message": "The ALB-owned Cognito client and user pool must use the same AWS Region.",
                    },
                },
            },
        )
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name=f"{prefix}_{suffix}",
                    value=f"module.{binding.pool_name}.{suffix}",
                )
                for suffix in ("user_pool_id", "user_pool_arn", "user_pool_domain")
            ],
            resources=[
                self._resource(
                    connection.target_name,
                    f"cognito_client_{binding.pool_name}_{config.listener_port}.tf",
                    content,
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_cognito_listener_bindings(connection.target_name, project)
        config = CognitoLoadBalancerConfig.model_validate(connection.connection_config)
        issues = [
            ConnectionIssue(
                severity="warning",
                message="Point the application hostname at this ALB and use a matching HTTPS certificate. The ALB needs outbound IPv4 HTTPS access to Cognito; an internal ALB may need NAT. The Terraform principal needs cognito-idp:DescribeUserPoolClient.",
            )
        ]
        if config.on_unauthenticated_request == "allow":
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="Unauthenticated requests are forwarded to the application; enforce required authentication in the backend.",
                )
            )
        return issues
