"""Rule-owned targets share scoped invocation roles and optional key grants."""

import hashlib

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.eventbridge_invocation import (
    EventBridgeInvocationConfig,
)
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier
from app.services.connection_handlers.kms_consumer import KmsConsumerGrants


class EventBridgeRoleTargetHandler(BaseConnectionHandler):
    def __init__(
        self,
        prefix: str,
        action: str,
        output: str,
        message: str,
        reject_fifo: bool = False,
    ):
        super().__init__()
        self._prefix = prefix
        self._action = action
        self._output_name = output
        self._message = message
        self._reject_fifo = reject_fifo

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message=self._message,
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = EventBridgeInvocationConfig.model_validate(
            connection.connection_config
        )
        rule, destination = connection.source_name, connection.target_name
        target = self._find_instance(destination, project)
        if self._reject_fifo and getattr(target.config, "fifo_topic", False):
            raise InvalidConnectionConfigError(
                rule,
                destination,
                connection.connection_type,
                [
                    {
                        "loc": ("fifo_topic",),
                        "msg": "This EventBridge connection requires a standard SNS topic",
                    }
                ],
            )
        target_id = config.target_id or safe_identifier(destination)
        for peer in project.connections:
            if peer.source_name != rule or peer.connection_type != "targets":
                continue
            peer_id = peer.connection_config.get("target_id") or safe_identifier(
                peer.target_name
            )
            if peer_id == target_id and (
                peer.target_name != destination
                or (peer.connection_config.get("input") or None) != config.input
            ):
                raise InvalidConnectionConfigError(
                    rule,
                    destination,
                    connection.connection_type,
                    [
                        {
                            "loc": ("target_id",),
                            "msg": "Target identifiers must uniquely select a destination and input within a rule",
                        }
                    ],
                )
        identifier = (
            self._prefix + "_" + hashlib.sha256(target_id.encode()).hexdigest()[:16]
        )
        variable = f"{identifier}_arn"
        grants = KmsConsumerGrants().augment(
            ConnectionContribution(
                iam=[
                    self._grant(
                        rule,
                        IAMStatement(
                            actions=[self._action],
                            resources=["${var." + variable + "}"],
                        ),
                    )
                ]
            ),
            destination,
            project,
        )
        statements = [
            {
                "Effect": grant.statement.effect,
                "Action": grant.statement.actions,
                "Resource": [
                    Expr(value[2:-1])
                    if value.startswith("${") and value.endswith("}")
                    else value
                    for value in grant.statement.resources
                ],
            }
            for grant in grants.iam
        ]
        grants.iam.clear()
        policy = self._renderer.render_json_policy
        resources = [
            self._renderer.render_resource(
                "aws_iam_role",
                identifier,
                {
                    "name_prefix": f"events-{self._prefix}-",
                    "assume_role_policy": policy(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {"Service": "events.amazonaws.com"},
                                    "Action": "sts:AssumeRole",
                                    "Condition": {
                                        "ArnEquals": {
                                            "aws:SourceArn": Expr(
                                                f"aws_cloudwatch_event_rule.{rule}.arn"
                                            )
                                        }
                                    },
                                }
                            ],
                        }
                    ),
                },
            ),
            self._renderer.render_resource(
                "aws_iam_role_policy",
                identifier,
                {
                    "role": Expr(f"aws_iam_role.{identifier}.id"),
                    "policy": policy(
                        {
                            "Version": "2012-10-17",
                            "Statement": statements,
                        }
                    ),
                },
            ),
        ]
        attrs = {
            "rule": Expr(f"aws_cloudwatch_event_rule.{rule}.name"),
            "target_id": target_id,
            "arn": Expr(f"var.{variable}"),
            "role_arn": Expr(f"aws_iam_role.{identifier}.arn"),
            "depends_on": Expr(f"[aws_iam_role_policy.{identifier}]"),
        }
        if self._reject_fifo:
            attrs["lifecycle"] = {
                "precondition": [
                    {
                        "condition": Expr(f'!endswith(var.{variable}, ".fifo")'),
                        "error_message": "Select a standard SNS topic for this EventBridge target.",
                    }
                ]
            }
        if config.input is not None:
            attrs["input"] = config.input
        resources.append(
            self._renderer.render_resource(
                "aws_cloudwatch_event_target", identifier, attrs
            )
        )
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=rule,
                    name=variable,
                    value=f"module.{destination}.{self._output_name}",
                )
            ],
            resources=[self._resource(rule, f"{identifier}.tf", "\n".join(resources))],
        )

        result.merge(grants)
        return result
