"""Execution-role access and runtime references for standard Kinesis clients."""

from typing import Literal

from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class KinesisAccessHandler(BaseConnectionHandler):
    def __init__(self, access: Literal["read", "write"]):
        super().__init__()
        self._actions = (
            [
                "kinesis:DescribeStream",
                "kinesis:DescribeStreamSummary",
                "kinesis:GetRecords",
                "kinesis:GetShardIterator",
                "kinesis:ListShards",
            ]
            if access == "read"
            else ["kinesis:PutRecord", "kinesis:PutRecords"]
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Application code must use the exported stream name or ARN to publish or poll records. This connection creates no Lambda event source mapping, enhanced fan-out consumer, or KCL lease tables. Network access and any externally configured customer-managed encryption-key permissions remain separate.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        source, target = connection.source_name, connection.target_name
        result = ConnectionContribution()
        for attribute in ("arn", "name"):
            variable = f"kinesis_{target}_{attribute}"
            result.inputs.append(
                ModuleInput(
                    module=source,
                    name=variable,
                    value=f"module.{target}.stream_{attribute}",
                    description="Connected Kinesis stream identity",
                )
            )
            result.outputs.append(
                self._output(
                    source,
                    variable,
                    f"var.{variable}",
                    "Pass this stream identity to application code",
                )
            )
        result.iam.append(
            self._grant(
                source,
                IAMStatement(
                    actions=self._actions,
                    resources=["${var.kinesis_" + target + "_arn}"],
                ),
            )
        )
        return result
