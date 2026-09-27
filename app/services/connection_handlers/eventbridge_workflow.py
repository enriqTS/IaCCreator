"""Rule-owned Step Functions invocation targets and least-privilege roles."""

import hashlib

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.eventbridge_workflow import EventBridgeWorkflowConfig
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class EventBridgeWorkflowHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Starts asynchronous workflow executions for matching events. The workflow execution role and definition remain separately configured. Events may be delivered more than once; make workflow actions idempotent. Configure delivery retries, dead-letter handling, alarms, and any workflow encryption permissions separately. Constant input replaces the matched event; no input transformer is generated.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = EventBridgeWorkflowConfig.model_validate(connection.connection_config)
        rule, workflow = connection.source_name, connection.target_name
        target_id = config.target_id or safe_identifier(workflow)
        for peer in project.connections:
            if peer.source_name != rule or peer.connection_type != "targets":
                continue
            peer_id = peer.connection_config.get("target_id") or safe_identifier(
                peer.target_name
            )
            if peer_id == target_id and (
                peer.target_name != workflow
                or (peer.connection_config.get("input") or None) != config.input
            ):
                raise InvalidConnectionConfigError(
                    rule,
                    workflow,
                    connection.connection_type,
                    [
                        {
                            "loc": ("target_id",),
                            "msg": "Target identifiers must uniquely select a destination and input within a rule",
                        }
                    ],
                )
        identifier = "workflow_" + hashlib.sha256(target_id.encode()).hexdigest()[:16]
        variable = f"{identifier}_arn"
        policy = self._renderer.render_json_policy
        resources = [
            self._renderer.render_resource(
                "aws_iam_role",
                identifier,
                {
                    "name_prefix": "events-workflow-",
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
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": ["states:StartExecution"],
                                    "Resource": Expr(f"var.{variable}"),
                                }
                            ],
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
        if config.input is not None:
            attrs["input"] = config.input
        resources.append(
            self._renderer.render_resource(
                "aws_cloudwatch_event_target", identifier, attrs
            )
        )
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=rule,
                    name=variable,
                    value=f"module.{workflow}.state_machine_arn",
                )
            ],
            resources=[self._resource(rule, f"{identifier}.tf", "\n".join(resources))],
        )
