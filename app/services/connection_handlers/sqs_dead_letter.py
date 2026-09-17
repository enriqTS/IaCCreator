"""Destination-owned redrive attachments avoid reciprocal module dependencies."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.generators.sqs_redrive import render_redrive
from app.models.connection_configs.configs import SqsDeadLetterConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class SQSDeadLetterHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Failed receives move messages to the selected dead-letter queue after max_receive_count. Set a dead-letter retention period longer than the source queue's, and configure consumer retries and visibility timeouts separately. FIFO dead-lettering can break end-to-end ordering. The allow policy owns the complete source list, limited to ten queues. Alarms, replay operations, consumer access, and decrypt access to original message keys remain separate.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        links = {}
        for item in project.connections:
            if (item.source_service, item.target_service, item.connection_type) != (
                ServiceType.SQS,
                ServiceType.SQS,
                "dead_letters_to",
            ):
                continue
            config = SqsDeadLetterConfig.model_validate(item.connection_config)
            value = (item.target_name, config.max_receive_count)
            if item.source_name in links and links[item.source_name] != value:
                self._reject(
                    connection,
                    "Each source queue requires one dead-letter destination and receive count",
                )
            links[item.source_name] = value
        for start in links:
            visited = set()
            node = start
            while node in links:
                if node in visited:
                    self._reject(
                        connection,
                        "Dead-letter queue connections must not form a cycle or point to themselves",
                    )
                visited.add(node)
                node = links[node][0]
        target = connection.target_name
        sources = sorted(
            source
            for source, (destination, _) in links.items()
            if destination == target
        )
        if len(sources) > 10:
            self._reject(
                connection,
                "A dead-letter allow policy supports at most 10 source queues",
            )
        destination = self._find_instance(target, project)
        result = ConnectionContribution()
        for source in sources:
            instance = self._find_instance(source, project)
            if bool(instance.config.fifo_queue) != bool(destination.config.fifo_queue):
                self._reject(
                    connection,
                    "Source and dead-letter queues must both be standard or both FIFO",
                )
            for attribute in ("arn", "url", "fifo_queue"):
                output = f"redrive_{attribute}"
                variable = f"redrive_{source}_{attribute}"
                result.outputs.append(
                    self._output(source, output, f"aws_sqs_queue.{source}.{attribute}")
                )
                result.inputs.append(
                    ModuleInput(
                        module=target,
                        name=variable,
                        type="bool" if attribute == "fifo_queue" else "string",
                        value=f"module.{source}.{output}",
                    )
                )
            result.resources.append(
                self._resource(
                    target,
                    f"redrive_{source}.tf",
                    render_redrive(source, target, links[source][1]),
                )
            )
        result.resources.append(
            self._resource(
                target,
                "redrive_allow.tf",
                self._renderer.render_resource(
                    "aws_sqs_queue_redrive_allow_policy",
                    "connected_sources",
                    {
                        "queue_url": Expr(f"aws_sqs_queue.{target}.url"),
                        "redrive_allow_policy": self._renderer.render_json_policy(
                            {
                                "redrivePermission": "byQueue",
                                "sourceQueueArns": [
                                    Expr(f"var.redrive_{source}_arn")
                                    for source in sources
                                ],
                            }
                        ),
                    },
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
            [{"loc": ("dead_letter",), "msg": message}],
        )
