"""Grant cache/user-scoped IAM login and export serverless client metadata."""

import hashlib

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.elasticache_serverless import (
    ServerlessCacheIamConfig,
)
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class ServerlessCacheIamHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Serverless caches use TLS. Requires an existing IAM-enabled cache user with identical ID and user name in the configured user group; authentication mode and group membership must be verified separately. The user's access string controls commands and keys. Application code must sign tokens for the cache name and Region with ResourceType=ServerlessCache, refresh 15-minute tokens, and reauthenticate long-lived connections before 12 hours. Use a cluster-aware TLS client. Network reachability, users, user groups, and credentials are not provisioned by this connection.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = ServerlessCacheIamConfig.model_validate(connection.connection_config)
        cache = self._find_instance(connection.target_name, project)
        if not cache.config.user_group_id or not cache.config.user_group_id.strip():
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("user_group_id",),
                        "msg": "Serverless IAM access requires an existing user group containing the selected IAM user",
                    }
                ],
            )
        cache.config._iam_client_access = True
        source, target = connection.source_name, connection.target_name
        ref = f"aws_elasticache_serverless_cache.{target}"
        identifier = "user_" + hashlib.sha256(config.user_id.encode()).hexdigest()[:16]
        binding = f"serverless_{target}_{identifier}"
        expressions = {
            "cache_arn": (f"{ref}.arn", "string"),
            "cache_name": (f"lower({ref}.name)", "string"),
            "engine": (f"{ref}.engine", "string"),
            "host": (f"one({ref}.endpoint).address", "string"),
            "port": (f"one({ref}.endpoint).port", "number"),
            "region": (f'split(":", {ref}.arn)[3]', "string"),
            f"{identifier}_arn": (
                f'format("arn:%s:elasticache:%s:%s:user:{config.user_id}", split(":", {ref}.arn)[1], split(":", {ref}.arn)[3], split(":", {ref}.arn)[4])',
                "string",
            ),
        }
        result = ConnectionContribution()
        for field, (expression, kind) in expressions.items():
            result.outputs.append(
                self._output(target, f"iam_client_{field}", expression)
            )
            result.inputs.append(
                ModuleInput(
                    module=source,
                    name=f"serverless_{target}_{field}",
                    value=f"module.{target}.iam_client_{field}",
                    type=kind,
                )
            )
        metadata = {
            field: Expr(f"var.serverless_{target}_{field}")
            for field in ("cache_name", "engine", "host", "port", "region")
        }
        metadata.update(
            user_id=config.user_id,
            user_name=config.user_id,
            tls=True,
            resource_type="ServerlessCache",
        )
        result.outputs.append(
            self._output(
                source,
                binding,
                self._renderer.render_expression(metadata),
                "Serverless cache IAM client configuration",
            )
        )
        result.iam.append(
            self._grant(
                source,
                IAMStatement(
                    actions=["elasticache:Connect"],
                    resources=[
                        "${var.serverless_" + target + "_cache_arn}",
                        "${var." + binding + "_arn}",
                    ],
                ),
            )
        )
        return result
