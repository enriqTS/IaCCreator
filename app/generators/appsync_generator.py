"""Terraform generator for AWS AppSync GraphQL APIs."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.appsync_config import AppSyncConfig
from app.models.ir_models import ResourceInstanceIR


class AppSyncGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, AppSyncConfig)
        attrs = {
            "name": instance.name,
            "authentication_type": Expr("var.authentication_type"),
            "xray_enabled": Expr("var.xray_enabled"),
        }
        if config.schema_definition is not None:
            attrs["schema"] = Expr("var.schema_definition")
        parts = [
            self._r.render_resource("aws_appsync_graphql_api", instance.name, attrs)
        ]
        if config.authentication_type == "API_KEY" and config.create_api_key:
            parts.append(
                self._r.render_resource(
                    "aws_appsync_api_key",
                    instance.name,
                    {
                        "api_id": Expr(f"aws_appsync_graphql_api.{instance.name}.id"),
                    },
                )
            )
        return "\n".join(parts)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, AppSyncConfig)
        fields = [
            ("authentication_type", "string", "Default authentication type"),
            ("create_api_key", "bool", "Create an API key"),
            ("xray_enabled", "bool", "Enable X-Ray tracing"),
        ]
        if config.schema_definition is not None:
            fields.append(("schema_definition", "string", "GraphQL schema document"))
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, AppSyncConfig)
        ref = f"aws_appsync_graphql_api.{instance.name}"
        parts = [
            self._r.render_output("graphql_api_id", f"{ref}.id", "GraphQL API ID"),
            self._r.render_output(
                "graphql_endpoint", f'{ref}.uris["GRAPHQL"]', "GraphQL endpoint"
            ),
            self._r.render_output("graphql_api_arn", f"{ref}.arn", "GraphQL API ARN"),
        ]
        if config.authentication_type == "API_KEY" and config.create_api_key:
            parts.append(
                self._r.render_output(
                    "api_key_id",
                    f"aws_appsync_api_key.{instance.name}.id",
                    "API key ID",
                )
            )
        return "\n".join(parts)
