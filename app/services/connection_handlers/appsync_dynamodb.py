"""AppSync-owned DynamoDB data sources and item resolvers."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.appsync_dynamodb_resolver import dynamodb_resolver_code
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.appsync_dynamodb import AppSyncDynamoDbConfig
from app.models.connection_configs.appsync_lambda import AppSyncLambdaConfig
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
from app.services.connection_handlers.appsync_dynamodb_keys import table_key_reference
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_references import managed_key

_ACTIONS = {
    "get_item": "dynamodb:GetItem",
    "put_item": "dynamodb:PutItem",
    "update_item": "dynamodb:UpdateItem",
    "delete_item": "dynamodb:DeleteItem",
}


class AppSyncDynamoDbHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The selected GraphQL field and arguments must exist in the API schema and use values compatible with the table keys. PutItem creates by default; set overwrite only when replacement is intended. External KMS key policies must permit the AppSync data-source role.",
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
            and item.target_service == ServiceType.DYNAMODB
            and item.connection_type == "resolves_with"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        instance = self._find_instance(api, project)
        if not instance.config.schema_definition:
            self._reject(
                connection,
                "schema_definition",
                "AppSync DynamoDB resolvers require a GraphQL schema definition",
            )
        fields = {}
        for item in peers:
            config = AppSyncDynamoDbConfig.model_validate(item.connection_config)
            target = self._find_instance(item.target_name, project)
            self._validate_table(item, config, target, project)
            key = (config.resolved_type_name, config.field_name)
            binding = (item.target_name, config)
            if key in fields and fields[key] != binding:
                self._reject(
                    item,
                    "field_name",
                    f"GraphQL field {key[0]}.{key[1]} has multiple DynamoDB resolvers",
                )
            fields[key] = binding
        for item in project.connections:
            if (
                item.source_name != api
                or item.target_service != ServiceType.LAMBDA
                or item.connection_type != "resolves_with"
            ):
                continue
            config = AppSyncLambdaConfig.model_validate(item.connection_config)
            if (config.type_name, config.field_name) in fields:
                self._reject(
                    item,
                    "field_name",
                    f"GraphQL field {config.type_name}.{config.field_name} has multiple data-source resolvers",
                )
        tables = sorted({name for name, _ in fields.values()})
        result = ConnectionContribution()
        api_ref = f"aws_appsync_graphql_api.{api}"
        for table in tables:
            result.inputs.extend(
                [
                    ModuleInput(
                        module=api,
                        name=f"appsync_{table}_table_name",
                        value=f"module.{table}.table_name",
                    ),
                    ModuleInput(
                        module=api,
                        name=f"appsync_{table}_table_arn",
                        value=f"module.{table}.table_arn",
                    ),
                ]
            )
            operations = sorted(
                {
                    _ACTIONS[config.operation]
                    for target, config in fields.values()
                    if target == table
                }
            )
            key_result, key_ref, lookup = table_key_reference(api, table, project)
            result.merge(key_result)
            result.resources.append(
                self._resource(
                    api,
                    f"dynamodb_datasource_{table}.tf",
                    self._data_source(api, table, operations, key_ref, lookup),
                )
            )
        for (type_name, field_name), (table, config) in sorted(fields.items()):
            target = self._find_instance(table, project)
            name = resolver_name(type_name, field_name)
            resolver = self._renderer.render_resource(
                "aws_appsync_resolver",
                name,
                {
                    "api_id": Expr(f"{api_ref}.id"),
                    "type": type_name,
                    "field": field_name,
                    "data_source": Expr(
                        f"aws_appsync_datasource.dynamodb_{table}.name"
                    ),
                    "code": dynamodb_resolver_code(config, target.config),
                    "runtime": {"name": "APPSYNC_JS", "runtime_version": "1.0.0"},
                },
            )
            result.resources.append(
                self._resource(api, f"dynamodb_{name}.tf", resolver)
            )
        return result

    def _data_source(
        self,
        api: str,
        table: str,
        actions: list[str],
        key_ref: Expr | None,
        lookup: str,
    ) -> str:
        api_ref = f"aws_appsync_graphql_api.{api}"
        name = f"dynamodb_{table}"
        role = self._renderer.render_resource(
            "aws_iam_role",
            f"{name}_role",
            {
                "name_prefix": "iac-appsync-",
                "assume_role_policy": assume_role_policy(self._renderer, api),
            },
        )
        statements = [
            {
                "Effect": "Allow",
                "Action": actions,
                "Resource": [Expr(f"var.appsync_{table}_table_arn")],
            }
        ]
        if key_ref:
            key_actions = ["kms:Decrypt"]
            if any(action != "dynamodb:GetItem" for action in actions):
                key_actions.append("kms:GenerateDataKey")
            statements.append(
                {"Effect": "Allow", "Action": key_actions, "Resource": [key_ref]}
            )
        policy = self._renderer.render_resource(
            "aws_iam_role_policy",
            f"{name}_access",
            {
                "name": "access-dynamodb",
                "role": Expr(f"aws_iam_role.{name}_role.id"),
                "policy": self._renderer.render_json_policy(
                    {"Version": "2012-10-17", "Statement": statements}
                ),
            },
        )
        data_source = self._renderer.render_resource(
            "aws_appsync_datasource",
            name,
            {
                "api_id": Expr(f"{api_ref}.id"),
                "name": data_source_name("dynamodb", table),
                "type": "AMAZON_DYNAMODB",
                "service_role_arn": Expr(f"aws_iam_role.{name}_role.arn"),
                "dynamodb_config": {
                    "table_name": Expr(f"var.appsync_{table}_table_name")
                },
                "depends_on": Expr(f"[aws_iam_role_policy.{name}_access]"),
            },
        )
        return lookup + role + policy + data_source

    def _validate_table(self, connection, config, target, project):
        table = target.config
        if config.range_argument and not table.range_key:
            self._reject(
                connection,
                "range_argument",
                "A sort-key argument requires a DynamoDB table with a sort key",
            )
        if config.update_attribute and config.update_attribute in {
            table.hash_key,
            table.range_key,
        }:
            self._reject(
                connection,
                "update_attribute",
                "UpdateItem cannot replace a table key attribute",
            )
        if (
            table.server_side_encryption_kms_key_arn
            and not table.server_side_encryption_enabled
            and not managed_key(connection.target_name, project)
        ):
            self._reject(
                connection,
                "server_side_encryption_enabled",
                "An external DynamoDB KMS key requires server-side encryption to be enabled",
            )

    @staticmethod
    def _reject(connection: ConnectionIR, field: str, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": (field,), "msg": message}],
        )
