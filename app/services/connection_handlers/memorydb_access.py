"""MemoryDB IAM login preserves external users, ACLs, and command permissions."""

import hashlib
import re

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.generators.memorydb_iam import existing_acl, existing_user
from app.models.connection_configs.memorydb import MemoryDbIamConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models.memorydb_config import MEMORYDB_IAM_VERSION_PATTERN
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class MemoryDbAccessHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Uses an existing MemoryDB IAM user in the configured external ACL; the user's access string controls commands and keys. Terraform reads user/ACL metadata and checks IAM mode and membership. Requires TLS and engine 7.0 or newer. Application code must generate and refresh IAM tokens using its runtime role and the exported cluster name, user, and Region. Network reachability remains separate. No passwords, users, or ACLs are created.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = MemoryDbIamConfig.model_validate(connection.connection_config)
        cluster = self._find_instance(connection.target_name, project)
        if (
            not cluster.config.tls_enabled
            or cluster.config.acl_name.strip().lower() in {"", "open-access"}
        ):
            self._reject(
                connection, "MemoryDB IAM login requires TLS and an explicit ACL"
            )
        if cluster.config.engine_version is not None and not re.match(
            MEMORYDB_IAM_VERSION_PATTERN, cluster.config.engine_version
        ):
            self._reject(connection, "MemoryDB IAM login requires engine 7.0 or newer")
        cluster.config._iam_client_access = True
        source, target = connection.source_name, connection.target_name
        identifier = (
            "iam_user_" + hashlib.sha256(config.user_name.encode()).hexdigest()[:16]
        )
        binding = f"memorydb_{target}_{identifier}"
        resource = f"aws_memorydb_cluster.{target}"
        result = ConnectionContribution(
            resources=[
                self._resource(target, "iam_client_acl.tf", existing_acl()),
                self._resource(
                    target,
                    f"{identifier}.tf",
                    existing_user(identifier, config.user_name),
                ),
            ]
        )
        expressions = {
            "cluster_arn": f"{resource}.arn",
            "cluster_name": f"{resource}.name",
            "host": f"one({resource}.cluster_endpoint).address",
            "port": f"tostring(one({resource}.cluster_endpoint).port)",
            "region": f'split(":", {resource}.arn)[3]',
        }
        for field, expression in expressions.items():
            output, variable = f"iam_client_{field}", f"memorydb_{target}_{field}"
            result.outputs.append(self._output(target, output, expression))
            result.inputs.append(
                ModuleInput(
                    module=source, name=variable, value=f"module.{target}.{output}"
                )
            )
        user_output = f"{identifier}_arn"
        result.outputs.append(
            self._output(
                target, user_output, f"data.aws_memorydb_user.{identifier}.arn"
            )
        )
        result.inputs.append(
            ModuleInput(
                module=source,
                name=f"{binding}_arn",
                value=f"module.{target}.{user_output}",
            )
        )
        metadata = {
            field: Expr(f"var.memorydb_{target}_{field}")
            for field in expressions
            if field != "cluster_arn"
        }
        metadata["user_name"] = config.user_name
        result.outputs.append(
            self._output(
                source,
                binding,
                self._renderer.render_expression(metadata),
                "MemoryDB IAM client configuration",
            )
        )
        result.iam.append(
            self._grant(
                source,
                IAMStatement(
                    actions=["memorydb:Connect"],
                    resources=[
                        "${var.memorydb_" + target + "_cluster_arn}",
                        "${var." + binding + "_arn}",
                    ],
                ),
            )
        )
        return result

    @staticmethod
    def _reject(connection: ConnectionIR, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": ("memorydb",), "msg": message}],
        )
