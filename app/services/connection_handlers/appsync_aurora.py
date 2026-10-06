"""AppSync-owned Aurora PostgreSQL Data API sources and row resolvers."""

import re

from app.exceptions import InvalidConnectionConfigError
from app.generators.appsync_aurora_resolver import aurora_resolver_code
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.appsync_aurora import AppSyncAuroraConfig
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


class AppSyncAuroraHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Requires an existing table and an externally prepared Secrets Manager credential for a database user with only the selected table privileges. Aurora PostgreSQL Data API engine/version support varies by Region. This connection creates an encrypted Serverless v2 writer, enables Data API, and manages the cluster master secret for bootstrap; the AppSync role does not read the master secret. Customer-managed credential keys need a permitting key policy.",
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
            and item.target_service == ServiceType.AURORA
            and item.connection_type == "resolves_with"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        instance = self._find_instance(api, project)
        if not instance.config.schema_definition:
            self._reject(
                connection,
                "schema_definition",
                "AppSync Aurora resolvers require a GraphQL schema definition",
            )
        fields = {}
        credentials = {}
        for item in peers:
            config = AppSyncAuroraConfig.model_validate(item.connection_config)
            target = self._find_instance(item.target_name, project)
            self._validate_cluster(item, config, target, project)
            key = (config.resolved_type_name, config.field_name)
            binding = (item.target_name, config)
            if key in fields and fields[key] != binding:
                self._reject(
                    item,
                    "field_name",
                    f"GraphQL field {key[0]}.{key[1]} has multiple Aurora resolvers",
                )
            fields[key] = binding
            credential = (
                config.credential_secret_arn,
                config.credential_kms_key_arn,
            )
            previous = credentials.get(item.target_name)
            if previous is not None and previous != credential:
                self._reject(
                    item,
                    "credential_secret_arn",
                    "One Aurora cluster must use one database-user credential for its AppSync data source",
                )
            credentials[item.target_name] = credential
        self._check_other_resolvers(api, fields, project)
        clusters = sorted(credentials)
        result = ConnectionContribution()
        for cluster in clusters:
            self._find_instance(cluster, project).config._appsync_data_api = True
            result.inputs.extend(
                [
                    ModuleInput(
                        module=api,
                        name=f"appsync_{cluster}_cluster_arn",
                        value=f"module.{cluster}.data_api_cluster_arn",
                    ),
                    ModuleInput(
                        module=api,
                        name=f"appsync_{cluster}_database_name",
                        value=f"module.{cluster}.database_name",
                    ),
                ]
            )
            result.resources.append(
                self._resource(
                    api,
                    f"aurora_datasource_{cluster}.tf",
                    self._data_source(api, cluster, *credentials[cluster]),
                )
            )
        for (type_name, field_name), (cluster, config) in sorted(fields.items()):
            name = resolver_name(type_name, field_name)
            resolver = self._renderer.render_resource(
                "aws_appsync_resolver",
                name,
                {
                    "api_id": Expr(f"aws_appsync_graphql_api.{api}.id"),
                    "type": type_name,
                    "field": field_name,
                    "data_source": Expr(
                        f"aws_appsync_datasource.aurora_{cluster}.name"
                    ),
                    "code": aurora_resolver_code(config),
                    "runtime": {"name": "APPSYNC_JS", "runtime_version": "1.0.0"},
                },
            )
            result.resources.append(self._resource(api, f"aurora_{name}.tf", resolver))
        return result

    def _data_source(
        self, api: str, cluster: str, secret_arn: str, kms_key_arn: str | None
    ) -> str:
        name = f"aurora_{cluster}"
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
                "Action": ["rds-data:ExecuteStatement"],
                "Resource": [Expr(f"var.appsync_{cluster}_cluster_arn")],
            },
            {
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": [secret_arn],
            },
        ]
        if kms_key_arn:
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": ["kms:Decrypt"],
                    "Resource": [kms_key_arn],
                }
            )
        policy = self._renderer.render_resource(
            "aws_iam_role_policy",
            f"{name}_access",
            {
                "name": "access-aurora",
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
                "name": data_source_name("aurora", cluster),
                "type": "RELATIONAL_DATABASE",
                "service_role_arn": Expr(f"aws_iam_role.{name}_role.arn"),
                "relational_database_config": {
                    "source_type": "RDS_HTTP_ENDPOINT",
                    "http_endpoint_config": {
                        "db_cluster_identifier": Expr(
                            f"var.appsync_{cluster}_cluster_arn"
                        ),
                        "aws_secret_store_arn": secret_arn,
                        "database_name": Expr(f"var.appsync_{cluster}_database_name"),
                    },
                },
                "depends_on": Expr(f"[aws_iam_role_policy.{name}_access]"),
            },
        )
        return role + policy + data_source

    def _validate_cluster(
        self, connection: ConnectionIR, binding: AppSyncAuroraConfig, target, project
    ):
        cluster = target.config
        if cluster.engine != "aurora-postgresql":
            self._reject(
                connection,
                "engine",
                "AppSync RDS Data API connections require an Aurora PostgreSQL cluster",
            )
        if not cluster.engine_version or not cluster.engine_version.strip():
            self._reject(
                connection,
                "engine_version",
                "AppSync Aurora Data API connections require an explicit engine version",
            )
        if not cluster.database_name:
            self._reject(
                connection,
                "database_name",
                "AppSync Aurora Data API connections require an initial database name",
            )
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,62}", cluster.database_name):
            self._reject(
                connection,
                "database_name",
                "AppSync Aurora database names must start with a letter and contain only letters, digits, or underscores",
            )
        region = target.provider_region or project.global_config.provider_region
        if binding.credential_secret_arn.split(":")[3] != region:
            self._reject(
                connection,
                "credential_secret_arn",
                "Database-user secret must be in the Aurora cluster Region",
            )
        if (
            binding.credential_kms_key_arn
            and binding.credential_kms_key_arn.split(":")[3] != region
        ):
            self._reject(
                connection,
                "credential_kms_key_arn",
                "Credential KMS key must be in the Aurora cluster Region",
            )

    def _check_other_resolvers(self, api: str, fields: dict, project: ProjectIR):
        models = {
            ServiceType.LAMBDA: AppSyncLambdaConfig,
            ServiceType.DYNAMODB: AppSyncDynamoDbConfig,
            ServiceType.OPENSEARCH: AppSyncOpenSearchConfig,
            ServiceType.EVENTBRIDGE: AppSyncEventBridgeConfig,
        }
        for item in project.connections:
            if item.source_name != api or item.connection_type != "resolves_with":
                continue
            model = models.get(item.target_service)
            if model is None:
                continue
            config = model.model_validate(item.connection_config)
            type_name = getattr(config, "resolved_type_name", None) or config.type_name
            key = (type_name, config.field_name)
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
