"""AppSync-owned OpenSearch data sources and index-scoped resolvers."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.appsync_opensearch_resolver import opensearch_resolver_code
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.appsync_dynamodb import AppSyncDynamoDbConfig
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

_OPERATIONS = {
    "get_document": ("es:ESHttpGet", "/_doc/*"),
    "search": ("es:ESHttpPost", "/_search"),
    "index_document": ("es:ESHttpPut", "/_doc/*"),
    "delete_document": ("es:ESHttpDelete", "/_doc/*"),
}


class AppSyncOpenSearchHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The selected GraphQL field and arguments must exist in the API schema. The domain must be publicly reachable by AppSync; index creation, domain policies, and fine-grained security role mappings remain external. This connection enforces HTTPS and disables explicit request-body indexes for the entire domain.",
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
            and item.target_service == ServiceType.OPENSEARCH
            and item.connection_type == "resolves_with"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        instance = self._find_instance(api, project)
        if not instance.config.schema_definition:
            self._reject(
                connection,
                "schema_definition",
                "AppSync OpenSearch resolvers require a GraphQL schema definition",
            )
        fields = {}
        for item in peers:
            config = AppSyncOpenSearchConfig.model_validate(item.connection_config)
            key = (config.resolved_type_name, config.field_name)
            binding = (item.target_name, config)
            if key in fields and fields[key] != binding:
                self._reject(
                    item,
                    "field_name",
                    f"GraphQL field {key[0]}.{key[1]} has multiple OpenSearch resolvers",
                )
            fields[key] = binding
        self._check_other_resolvers(api, fields, project)
        domains = sorted({name for name, _ in fields.values()})
        result = ConnectionContribution()
        api_ref = f"aws_appsync_graphql_api.{api}"
        for domain in domains:
            self._find_instance(domain, project).config._index_client_access = True
            result.inputs.extend(
                [
                    ModuleInput(
                        module=api,
                        name=f"appsync_{domain}_domain_arn",
                        value=f"module.{domain}.domain_arn",
                    ),
                    ModuleInput(
                        module=api,
                        name=f"appsync_{domain}_domain_endpoint",
                        value=f"module.{domain}.domain_endpoint",
                    ),
                ]
            )
            grants = sorted(
                {
                    (config.index_name, *_OPERATIONS[config.operation])
                    for target, config in fields.values()
                    if target == domain
                }
            )
            result.resources.append(
                self._resource(
                    api,
                    f"opensearch_datasource_{domain}.tf",
                    self._data_source(api, domain, grants),
                )
            )
        for (type_name, field_name), (domain, config) in sorted(fields.items()):
            name = resolver_name(type_name, field_name)
            resolver = self._renderer.render_resource(
                "aws_appsync_resolver",
                name,
                {
                    "api_id": Expr(f"{api_ref}.id"),
                    "type": type_name,
                    "field": field_name,
                    "data_source": Expr(
                        f"aws_appsync_datasource.opensearch_{domain}.name"
                    ),
                    "code": opensearch_resolver_code(config),
                    "runtime": {"name": "APPSYNC_JS", "runtime_version": "1.0.0"},
                },
            )
            result.resources.append(
                self._resource(api, f"opensearch_{name}.tf", resolver)
            )
        return result

    def _data_source(
        self, api: str, domain: str, grants: list[tuple[str, str, str]]
    ) -> str:
        name = f"opensearch_{domain}"
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
                "Action": [action],
                "Resource": [
                    Expr(f'format("%s/{index}{path}", var.appsync_{domain}_domain_arn)')
                ],
            }
            for index, action, path in grants
        ]
        policy = self._renderer.render_resource(
            "aws_iam_role_policy",
            f"{name}_access",
            {
                "name": "access-opensearch",
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
                "api_id": Expr(f"aws_appsync_graphql_api.{api}.id"),
                "name": data_source_name("opensearch", domain),
                "type": "AMAZON_OPENSEARCH_SERVICE",
                "service_role_arn": Expr(f"aws_iam_role.{name}_role.arn"),
                "opensearchservice_config": {
                    "endpoint": Expr(
                        f'format("https://%s", var.appsync_{domain}_domain_endpoint)'
                    )
                },
                "depends_on": Expr(f"[aws_iam_role_policy.{name}_access]"),
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
