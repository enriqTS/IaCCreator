"""AppSync-owned EventBridge data sources and event-publishing resolvers."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.appsync_eventbridge_resolver import eventbridge_resolver_code
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.appsync_dynamodb import AppSyncDynamoDbConfig
from app.models.connection_configs.appsync_eventbridge import AppSyncEventBridgeConfig
from app.models.connection_configs.appsync_lambda import AppSyncLambdaConfig
from app.models.connection_configs.appsync_opensearch import AppSyncOpenSearchConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.appsync_common import (
    assume_role_policy,
    data_source_name,
    resolver_name,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class AppSyncEventBridgeHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The selected GraphQL field must exist in the API schema, accept an input object for event detail, and return an ID-compatible value. EventBridge rules and targets must be configured separately; publication does not guarantee a rule match or target delivery.",
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
            and item.target_service == ServiceType.EVENTBRIDGE
            and item.connection_type == "resolves_with"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        instance = self._find_instance(api, project)
        if not instance.config.schema_definition:
            self._reject(
                connection,
                "schema_definition",
                "AppSync EventBridge resolvers require a GraphQL schema definition",
            )
        fields = {}
        for item in peers:
            config = AppSyncEventBridgeConfig.model_validate(item.connection_config)
            key = (config.type_name, config.field_name)
            binding = (item.target_name, config)
            if key in fields and fields[key] != binding:
                self._reject(
                    item,
                    "field_name",
                    f"GraphQL field {key[0]}.{key[1]} has multiple EventBridge resolvers",
                )
            fields[key] = binding
        self._check_other_resolvers(api, fields, project)
        buses = sorted({name for name, _ in fields.values()})
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=api,
                    name=f"appsync_{bus}_event_bus_arn",
                    value=f"module.{bus}.event_bus_arn",
                )
                for bus in buses
            ]
        )
        for bus in buses:
            result.resources.append(
                self._resource(
                    api,
                    f"eventbridge_datasource_{bus}.tf",
                    self._data_source(api, bus),
                )
            )
        for (type_name, field_name), (bus, config) in sorted(fields.items()):
            name = resolver_name(type_name, field_name)
            resolver = self._renderer.render_resource(
                "aws_appsync_resolver",
                name,
                {
                    "api_id": Expr(f"aws_appsync_graphql_api.{api}.id"),
                    "type": type_name,
                    "field": field_name,
                    "data_source": Expr(
                        f"aws_appsync_datasource.eventbridge_{bus}.name"
                    ),
                    "code": eventbridge_resolver_code(config),
                    "runtime": {"name": "APPSYNC_JS", "runtime_version": "1.0.0"},
                },
            )
            result.resources.append(
                self._resource(api, f"eventbridge_{name}.tf", resolver)
            )
        return result

    def _data_source(self, api: str, bus: str) -> str:
        name = f"eventbridge_{bus}"
        role = self._renderer.render_resource(
            "aws_iam_role",
            f"{name}_role",
            {
                "name_prefix": "iac-appsync-",
                "assume_role_policy": assume_role_policy(self._renderer, api),
            },
        )
        policy = self._renderer.render_resource(
            "aws_iam_role_policy",
            f"{name}_publish",
            {
                "name": "publish-events",
                "role": Expr(f"aws_iam_role.{name}_role.id"),
                "policy": self._renderer.render_json_policy(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": ["events:PutEvents"],
                                "Resource": [Expr(f"var.appsync_{bus}_event_bus_arn")],
                            }
                        ],
                    }
                ),
            },
        )
        data_source = self._renderer.render_resource(
            "aws_appsync_datasource",
            name,
            {
                "api_id": Expr(f"aws_appsync_graphql_api.{api}.id"),
                "name": data_source_name("eventbridge", bus),
                "type": "AMAZON_EVENTBRIDGE",
                "service_role_arn": Expr(f"aws_iam_role.{name}_role.arn"),
                "event_bridge_config": {
                    "event_bus_arn": Expr(f"var.appsync_{bus}_event_bus_arn")
                },
                "depends_on": Expr(f"[aws_iam_role_policy.{name}_publish]"),
            },
        )
        return role + policy + data_source

    def _check_other_resolvers(self, api: str, fields: dict, project: ProjectIR):
        for item in project.connections:
            if item.source_name != api or item.connection_type != "resolves_with":
                continue
            if item.target_service == ServiceType.LAMBDA:
                config = AppSyncLambdaConfig.model_validate(item.connection_config)
                key = (config.type_name, config.field_name)
            elif item.target_service == ServiceType.DYNAMODB:
                config = AppSyncDynamoDbConfig.model_validate(item.connection_config)
                key = (config.resolved_type_name, config.field_name)
            elif item.target_service == ServiceType.OPENSEARCH:
                config = AppSyncOpenSearchConfig.model_validate(item.connection_config)
                key = (config.resolved_type_name, config.field_name)
            else:
                continue
            if key in fields:
                self._reject(
                    item,
                    "field_name",
                    f"GraphQL field {key[0]}.{key[1]} has multiple data-source resolvers",
                )

    @staticmethod
    def _reject(connection: ConnectionIR, field: str, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": (field,), "msg": message}],
        )
