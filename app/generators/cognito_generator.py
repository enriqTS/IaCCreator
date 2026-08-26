"""Terraform generator for Cognito user pools."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.cognito_config import CognitoConfig
from app.models.ir_models import ResourceInstanceIR


class CognitoGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, CognitoConfig)
        attrs = {
            "name": instance.name,
            "username_attributes": [Expr("var.username_attributes")],
            "mfa_configuration": Expr("var.mfa_configuration"),
        }
        if config.auto_verified_attributes:
            attrs["auto_verified_attributes"] = [Expr("var.username_attributes")]
        parts = [self._r.render_resource("aws_cognito_user_pool", instance.name, attrs)]
        if config.create_client:
            parts.append(
                self._r.render_resource(
                    "aws_cognito_user_pool_client",
                    instance.name,
                    {
                        "name": f"{instance.name}-client",
                        "user_pool_id": Expr(
                            f"aws_cognito_user_pool.{instance.name}.id"
                        ),
                        "generate_secret": False,
                    },
                )
            )
        return "\n".join(parts)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, CognitoConfig)
        return "\n".join(
            [
                self._r.render_variable(
                    "username_attributes", "string", "Username attribute"
                ),
                self._r.render_variable(
                    "auto_verified_attributes", "bool", "Automatically verify usernames"
                ),
                self._r.render_variable("mfa_configuration", "string", "MFA mode"),
                self._r.render_variable(
                    "create_client", "bool", "Create an application client"
                ),
            ]
        )

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, CognitoConfig)
        ref = f"aws_cognito_user_pool.{instance.name}"
        parts = [
            self._r.render_output("user_pool_id", f"{ref}.id", "User pool ID"),
            self._r.render_output("user_pool_arn", f"{ref}.arn", "User pool ARN"),
            self._r.render_output("endpoint", f"{ref}.endpoint", "User pool endpoint"),
        ]
        if config.create_client:
            parts.append(
                self._r.render_output(
                    "client_id",
                    f"aws_cognito_user_pool_client.{instance.name}.id",
                    "Application client ID",
                )
            )
        return "\n".join(parts)
