"""Encrypted awslogs callers use exact keys through regional Logs with group context."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.ir_models import (
    ConnectionContribution,
    IAMStatement,
    ModuleResource,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.ecs_logs_bindings import EcsLogBinding
from app.services.connection_handlers.kms_consumer import KmsConsumerGrants


def ecs_log_encryption(
    source: str,
    bindings: list[EcsLogBinding],
    project: ProjectIR,
    renderer: HCLRenderer,
) -> ConnectionContribution:
    result = ConnectionContribution()
    statements = []
    groups = {binding.log_group: binding.container_name for binding in bindings}
    for group, container in sorted(groups.items()):
        contribution = KmsConsumerGrants().augment(
            ConnectionContribution(
                iam=[
                    BaseConnectionHandler._grant(
                        source,
                        IAMStatement(actions=["logs:PutLogEvents"], resources=["*"]),
                    )
                ]
            ),
            group,
            project,
        )
        arn = f"var.ecs_logs[{renderer.render_expression(container)}].arn"
        for grant in contribution.iam[1:]:
            service = Expr(
                '"logs.${data.aws_region.ecs_logs.region}.${data.aws_partition.ecs_logs.dns_suffix}"'
            )
            keys = [Expr(value[2:-1]) for value in grant.statement.resources]
            statements.append(
                {
                    "Effect": grant.statement.effect,
                    "Action": [
                        action
                        for action in grant.statement.actions
                        if action != "kms:DescribeKey"
                    ],
                    "Resource": keys,
                    "Condition": {
                        "StringEquals": {
                            "kms:ViaService": service,
                            "kms:EncryptionContext:aws:logs:arn": Expr(
                                f'trimsuffix({arn}, ":*")'
                            ),
                        }
                    },
                }
            )
            statements.append(
                {
                    "Effect": grant.statement.effect,
                    "Action": ["kms:DescribeKey"],
                    "Resource": keys,
                    "Condition": {"StringEquals": {"kms:ViaService": service}},
                }
            )
        contribution.iam.clear()
        result.merge(contribution)
    if statements:
        result.resources.append(
            ModuleResource(
                module=source,
                filename="application_log_encryption.tf",
                content=renderer.render_resource(
                    "aws_iam_role_policy",
                    f"{source}_application_logs",
                    {
                        "name_prefix": "application-logs-",
                        "role": Expr(f"aws_iam_role.{source}_role.id"),
                        "policy": renderer.render_json_policy(
                            {"Version": "2012-10-17", "Statement": statements}
                        ),
                    },
                ),
            )
        )
    return result
