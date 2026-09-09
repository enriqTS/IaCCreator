"""One queue-owned policy authorizes all connected SNS and EventBridge publishers."""

from app.generators.hcl_renderer import Expr
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler

_DELIVERY_SOURCES = {
    ServiceType.SNS: ("sns.amazonaws.com", "topic_arn"),
    ServiceType.EVENTBRIDGE: ("events.amazonaws.com", "rule_arn"),
}


class QueueDeliveryPolicy(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        peers = [
            item
            for item in project.connections
            if item.target_name == connection.target_name
            and item.target_service == ServiceType.SQS
            and item.source_service in _DELIVERY_SOURCES
        ]
        if not peers or connection is not peers[0]:
            return ConnectionContribution()
        queue = connection.target_name
        result = ConnectionContribution()
        statements = []
        for service, (principal, output) in _DELIVERY_SOURCES.items():
            sources = sorted(
                {item.source_name for item in peers if item.source_service == service}
            )
            if not sources:
                continue
            variable = f"delivery_{service.value}_arns"
            result.inputs.append(
                ModuleInput(
                    module=queue,
                    name=variable,
                    type="list(string)",
                    value="["
                    + ", ".join(f"module.{source}.{output}" for source in sources)
                    + "]",
                    description="Sources authorized to deliver messages",
                )
            )
            statements.append(
                {
                    "Effect": "Allow",
                    "Principal": {"Service": principal},
                    "Action": "SQS:SendMessage",
                    "Resource": Expr(f"aws_sqs_queue.{queue}.arn"),
                    "Condition": {
                        "ArnEquals": {"aws:SourceArn": Expr(f"var.{variable}")}
                    },
                }
            )
        result.resources.append(
            self._resource(
                queue,
                "policy_delivery.tf",
                self._renderer.render_resource(
                    "aws_sqs_queue_policy",
                    "delivery",
                    {
                        "queue_url": Expr(f"aws_sqs_queue.{queue}.url"),
                        "policy": self._renderer.render_json_policy(
                            {"Version": "2012-10-17", "Statement": statements}
                        ),
                    },
                ),
            )
        )
        return result
