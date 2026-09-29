"""AppSync-owned Lambda data sources and direct resolvers."""

from hashlib import sha256

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.appsync_lambda import AppSyncLambdaConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


def _data_source_name(function: str) -> str:
    suffix = sha256(function.encode()).hexdigest()[:8]
    return f"lambda_{safe_identifier(function)[:40]}_{suffix}"


def _resolver_name(type_name: str, field_name: str) -> str:
    suffix = sha256(f"{type_name}.{field_name}".encode()).hexdigest()[:8]
    return f"resolver_{type_name[:24]}_{field_name[:24]}_{suffix}"


class AppSyncLambdaHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The selected GraphQL type and field must exist in the API schema. The direct resolver sends the AppSync context to Lambda and returns its response as the field value.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        api = connection.source_name
        peers = [
            item
            for item in project.connections
            if item.source_name == api
            and item.target_service == ServiceType.LAMBDA
            and item.connection_type == "resolves_with"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        instance = self._find_instance(api, project)
        if not instance.config.schema_definition:
            self._reject(
                connection,
                "schema_definition",
                "AppSync Lambda resolvers require a GraphQL schema definition",
            )
        fields = {}
        for item in peers:
            config = AppSyncLambdaConfig.model_validate(item.connection_config)
            key = (config.type_name, config.field_name)
            if key in fields and fields[key] != item.target_name:
                self._reject(
                    item,
                    "field_name",
                    f"GraphQL field {config.type_name}.{config.field_name} has multiple Lambda resolvers",
                )
            fields[key] = item.target_name
        functions = sorted(set(fields.values()))
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=api,
                    name=f"appsync_{function}_function_arn",
                    value=f"module.{function}.function_arn",
                )
                for function in functions
            ]
        )
        api_ref = f"aws_appsync_graphql_api.{api}"
        for function in functions:
            resource_name = f"lambda_{function}"
            role = self._renderer.render_resource(
                "aws_iam_role",
                f"{resource_name}_role",
                {
                    "name_prefix": "iac-appsync-",
                    "assume_role_policy": self._renderer.render_json_policy(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {"Service": "appsync.amazonaws.com"},
                                    "Action": "sts:AssumeRole",
                                    "Condition": {
                                        "ArnEquals": {
                                            "aws:SourceArn": Expr(f"{api_ref}.arn")
                                        }
                                    },
                                }
                            ],
                        }
                    ),
                },
            )
            policy = self._renderer.render_resource(
                "aws_iam_role_policy",
                f"{resource_name}_invoke",
                {
                    "name": "invoke-lambda",
                    "role": Expr(f"aws_iam_role.{resource_name}_role.id"),
                    "policy": self._renderer.render_json_policy(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": ["lambda:InvokeFunction"],
                                    "Resource": [
                                        Expr(f"var.appsync_{function}_function_arn")
                                    ],
                                }
                            ],
                        }
                    ),
                },
            )
            data_source = self._renderer.render_resource(
                "aws_appsync_datasource",
                resource_name,
                {
                    "api_id": Expr(f"{api_ref}.id"),
                    "name": _data_source_name(function),
                    "type": "AWS_LAMBDA",
                    "service_role_arn": Expr(f"aws_iam_role.{resource_name}_role.arn"),
                    "lambda_config": {
                        "function_arn": Expr(f"var.appsync_{function}_function_arn")
                    },
                    "depends_on": Expr(f"[aws_iam_role_policy.{resource_name}_invoke]"),
                },
            )
            result.resources.append(
                self._resource(
                    api,
                    f"lambda_datasource_{function}.tf",
                    role + policy + data_source,
                )
            )
        for (type_name, field_name), function in sorted(fields.items()):
            name = _resolver_name(type_name, field_name)
            resolver = self._renderer.render_resource(
                "aws_appsync_resolver",
                name,
                {
                    "api_id": Expr(f"{api_ref}.id"),
                    "type": type_name,
                    "field": field_name,
                    "data_source": Expr(
                        f"aws_appsync_datasource.lambda_{function}.name"
                    ),
                },
            )
            result.resources.append(self._resource(api, f"lambda_{name}.tf", resolver))
        return result

    @staticmethod
    def _reject(connection: ConnectionIR, field: str, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": (field,), "msg": message}],
        )
