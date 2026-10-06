"""Aggregate Cognito providers into the owning AppSync API's configuration."""

from app.exceptions import InvalidConnectionConfigError
from app.models.appsync_authentication import CognitoUserPoolBinding
from app.models.connection_configs.cognito_appsync import CognitoAppSyncConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class CognitoAppSyncHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        config = CognitoAppSyncConfig.model_validate(connection.connection_config)
        issues = []
        if config.mode == "additional":
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="Additional Cognito authentication requires @aws_cognito_user_pools directives on the intended GraphQL fields and returned types. Use these directives instead of @aws_auth when multiple authentication modes are enabled.",
                )
            )
        elif config.default_action == "DENY":
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="Default DENY requires explicit @aws_auth group directives for field access and existing Cognito group memberships.",
                )
            )
        if not config.restrict_to_client:
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="Client filtering is disabled: tokens from any application client in this Cognito user pool can authenticate. GraphQL authorization remains configured in the schema and resolvers.",
                )
            )
        return issues

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        peers = [
            item
            for item in project.connections
            if item.target_name == connection.target_name
            and item.source_service == ServiceType.COGNITO
            and item.connection_type == "authenticates"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        providers = {}
        for item in peers:
            config = CognitoAppSyncConfig.model_validate(item.connection_config)
            previous = providers.get(item.source_name)
            if previous is not None and previous != config:
                self._reject(
                    item,
                    "mode",
                    "One Cognito user pool must have one authentication configuration per AppSync API",
                )
            providers[item.source_name] = config
            pool = self._find_instance(item.source_name, project)
            if config.restrict_to_client and not pool.config.create_client:
                self._reject(
                    item,
                    "restrict_to_client",
                    "Client-restricted authentication requires Cognito create_client to be enabled",
                )
        defaults = [config for config in providers.values() if config.mode == "default"]
        if len(defaults) > 1:
            self._reject(
                connection,
                "mode",
                "An AppSync API can have only one default Cognito provider",
            )
        if defaults and defaults[0].default_action == "DENY" and len(providers) > 1:
            self._reject(
                connection,
                "default_action",
                "Default Cognito field access must be ALLOW when additional authentication providers are configured",
            )
        result = ConnectionContribution()
        bindings = []
        for name, config in sorted(providers.items()):
            prefix = f"cognito_{name}"
            values = {
                "user_pool_id": f"module.{name}.user_pool_id",
                "region": f"module.{name}.appsync_user_pool_region",
            }
            if config.restrict_to_client:
                values["client_id"] = f"module.{name}.client_id"
            result.inputs.extend(
                ModuleInput(
                    module=connection.target_name,
                    name=f"{prefix}_{suffix}",
                    value=value,
                )
                for suffix, value in values.items()
            )
            result.outputs.append(
                self._output(
                    name,
                    "appsync_user_pool_region",
                    f'split(":", aws_cognito_user_pool.{name}.arn)[3]',
                    "Region of the Cognito user pool used by AppSync",
                )
            )
            bindings.append(
                CognitoUserPoolBinding(
                    mode=config.mode,
                    user_pool_id_input=f"{prefix}_user_pool_id",
                    region_input=f"{prefix}_region",
                    client_id_input=f"{prefix}_client_id"
                    if config.restrict_to_client
                    else None,
                    default_action=config.default_action,
                )
            )
        self._find_instance(
            connection.target_name, project
        ).config._cognito_authentication = bindings
        return result

    @staticmethod
    def _reject(connection: ConnectionIR, field: str, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": (field,), "msg": message}],
        )
