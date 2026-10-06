"""Render connection-derived AppSync authentication configuration."""

from app.generators.hcl_renderer import Expr
from app.models.appsync_authentication import CognitoUserPoolBinding
from app.models.input_models.appsync_config import AppSyncConfig


def _user_pool_config(binding: CognitoUserPoolBinding) -> dict:
    attrs = {
        "user_pool_id": Expr(f"var.{binding.user_pool_id_input}"),
        "aws_region": Expr(f"var.{binding.region_input}"),
    }
    if binding.client_id_input:
        attrs["app_id_client_regex"] = Expr(
            f'format("^%s$", var.{binding.client_id_input})'
        )
    return attrs


def authentication_attributes(config: AppSyncConfig) -> dict:
    attrs: dict = {"authentication_type": Expr("var.authentication_type")}
    additional = []
    for binding in config._cognito_authentication:
        pool = _user_pool_config(binding)
        if binding.mode == "default":
            attrs["authentication_type"] = "AMAZON_COGNITO_USER_POOLS"
            pool["default_action"] = binding.default_action
            attrs["user_pool_config"] = pool
        else:
            additional.append(
                {
                    "authentication_type": "AMAZON_COGNITO_USER_POOLS",
                    "user_pool_config": pool,
                }
            )
    if additional:
        attrs["additional_authentication_provider"] = additional
    return attrs


def creates_api_key(config: AppSyncConfig) -> bool:
    return (
        config.authentication_type == "API_KEY"
        and config.create_api_key
        and not any(item.mode == "default" for item in config._cognito_authentication)
    )
