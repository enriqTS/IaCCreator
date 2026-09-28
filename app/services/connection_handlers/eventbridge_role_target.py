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
    config_model = EventBridgeInvocationConfig

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
        config = self.config_model.model_validate(connection.connection_config)
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
                or self.config_model.model_validate(peer.connection_config).model_dump(
                    exclude={"target_id"}
                )
                != config.model_dump(exclude={"target_id"})
            ):
                raise InvalidConnectionConfigError(
                    rule,
                    destination,
                    connection.connection_type,
                    [
                        {
                            "loc": ("target_id",),
                            "msg": "Target identifiers must uniquely select a destination and settings within a rule",
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
                            resources=[self.grant_resource(variable, config)],
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
                    self.policy_resource(value) for value in grant.statement.resources
                ],
            }
            for grant in grants.iam
        ]
        statements = self.policy_statements(statements, variable, identifier, config)
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
            "arn": self.target_arn(variable, config),
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
        if getattr(config, "input", None) is not None:
            attrs["input"] = config.input
        attrs.update(self.target_attributes(config, identifier))
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
                    value=f"module.{destination}.{self.output_name(destination)}",
                ),
                *self.additional_inputs(rule, destination, identifier, config),
            ],
            resources=[self._resource(rule, f"{identifier}.tf", "\n".join(resources))],
        )

        result.merge(grants)
        return result

    def target_attributes(
        self, config: EventBridgeInvocationConfig, identifier: str
    ) -> dict:
        return {}

    def additional_inputs(
        self,
        rule: str,
        destination: str,
        identifier: str,
        config: EventBridgeInvocationConfig,
    ) -> list[ModuleInput]:
        return []

    def policy_statements(
        self,
        statements: list[dict],
        variable: str,
        identifier: str,
        config: EventBridgeInvocationConfig,
    ) -> list[dict]:
        return statements

    def grant_resource(self, variable: str, config: EventBridgeInvocationConfig) -> str:
        return "${var." + variable + "}"

    def target_arn(self, variable: str, config: EventBridgeInvocationConfig) -> Expr:
        return Expr(f"var.{variable}")

    def policy_resource(self, value: str) -> Expr | str:
        if value.startswith("${") and value.endswith("}"):
            return Expr(value[2:-1])
        if value.startswith("${") and "}" in value:
            return Expr(f'"{value}"')
        return value

    def output_name(self, destination: str) -> str:
        return self._output_name
