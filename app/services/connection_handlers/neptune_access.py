"""Neptune graph query permissions use immutable cluster data-resource ARNs."""

import re
from typing import Literal

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_previews import ConnectionIssue
from app.models.input_models.neptune_config import NEPTUNE_DATA_AUTH_VERSION_PATTERN
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class NeptuneAccessHandler(BaseConnectionHandler):
    def __init__(self, access: Literal["read", "write"]):
        super().__init__()
        self._actions = ["neptune-db:ReadDataViaQuery"]
        if access == "write":
            self._actions.extend(
                ["neptune-db:WriteDataViaQuery", "neptune-db:DeleteDataViaQuery"]
            )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Enables IAM authentication for the cluster, so all graph clients must use SigV4-signed requests over TLS. Requires Neptune engine 1.2.0.0 or newer and separately provisioned cluster instances, VPC routing, and security groups. Application code uses the exported endpoint, port, and Region. Write access includes graph reads and query deletes; bulk loading, reset, streams, and query administration are separate. No database passwords are created.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        cluster = self._find_instance(connection.target_name, project)
        version = cluster.config.engine_version
        if version is not None and not re.match(
            NEPTUNE_DATA_AUTH_VERSION_PATTERN, version
        ):
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("engine_version",),
                        "msg": "Neptune graph IAM access requires engine 1.2.0.0 or newer",
                    }
                ],
            )
        cluster.config._iam_graph_access = True
        source, target = connection.source_name, connection.target_name
        resource = f"aws_neptune_cluster.{target}"
        arn = f"{resource}.arn"
        expressions = {
            "data_arn": f'format("arn:%s:neptune-db:%s:%s:%s/*", split(":", {arn})[1], split(":", {arn})[3], split(":", {arn})[4], {resource}.cluster_resource_id)',
            "host": f"{resource}.endpoint",
            "reader_host": f"{resource}.reader_endpoint",
            "port": f"tostring({resource}.port)",
            "region": f'split(":", {arn})[3]',
        }
        result = ConnectionContribution()
        for field, expression in expressions.items():
            output = f"graph_client_{field}"
            variable = f"neptune_{target}_{field}"
            result.outputs.append(self._output(target, output, expression))
            result.inputs.append(
                ModuleInput(
                    module=source, name=variable, value=f"module.{target}.{output}"
                )
            )
            result.outputs.append(
                self._output(
                    source,
                    variable,
                    f"var.{variable}",
                    "IAM-authenticated Neptune client metadata",
                )
            )
        result.iam.append(
            self._grant(
                source,
                IAMStatement(
                    actions=self._actions,
                    resources=["${var.neptune_" + target + "_data_arn}"],
                ),
            )
        )
        return result
