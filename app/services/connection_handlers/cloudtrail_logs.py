"""Trail-owned service roles deliver audit events to managed CloudWatch groups."""

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.cloudtrail_logs import (
    cloudtrail_log_stream_arn,
    render_cloudtrail_logs_role,
)
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_consumer import KmsConsumerGrants
from app.services.connection_handlers.kms_external_policy import (
    external_service_key_issues,
)


class CloudTrailLogsHandler(BaseConnectionHandler):
    def _check_destination(self, connection: ConnectionIR, project: ProjectIR) -> None:
        targets = {
            item.target_name
            for item in project.connections
            if item.source_name == connection.source_name
            and item.source_service == ServiceType.CLOUDTRAIL
            and item.target_service == ServiceType.CLOUDWATCH
            and item.connection_type == "logs_to"
        }
        if len(targets) > 1:
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("target",),
                        "msg": "A CloudTrail trail supports only one CloudWatch log group",
                    }
                ],
            )
        trail = self._find_instance(connection.source_name, project)
        group = self._find_instance(connection.target_name, project)
        for environment in project.environments:
            override = environment.variables.get("region")
            source_region = (
                override
                or trail.provider_region
                or project.global_config.provider_region
            )
            target_region = (
                override
                or group.provider_region
                or project.global_config.provider_region
            )
            if source_region != target_region:
                raise CrossRegionConnectionError(
                    trail.name,
                    source_region,
                    group.name,
                    target_region,
                    connection.connection_type,
                )

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        self._check_destination(connection, project)
        name = connection.source_name
        self._find_instance(name, project).config._cloudwatch_logs = True
        resource = f"{name}_cloudwatch_logs"
        grants = KmsConsumerGrants().augment(
            ConnectionContribution(
                iam=[
                    self._grant(
                        name,
                        IAMStatement(
                            actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                            resources=["${var.cloud_watch_logs_group_arn}"],
                        ),
                    )
                ]
            ),
            connection.target_name,
            project,
        )
        statements = [
            {
                "Effect": "Allow",
                "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": cloudtrail_log_stream_arn(),
            }
        ]
        for grant in grants.iam[1:]:
            statements.append(
                {
                    "Effect": grant.statement.effect,
                    "Action": grant.statement.actions,
                    "Resource": [
                        Expr(value[2:-1]) for value in grant.statement.resources
                    ],
                    "Condition": {
                        "StringEquals": {
                            "kms:ViaService": Expr(
                                '"logs.${data.aws_region.cloudtrail_logs.region}.${data.aws_partition.cloudtrail_logs.dns_suffix}"'
                            )
                        }
                    },
                }
            )
        grants.iam.clear()
        content = render_cloudtrail_logs_role(name, statements, self._renderer)
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=name,
                    name="cloud_watch_logs_group_arn",
                    value=f"module.{connection.target_name}.log_group_arn",
                    description="Managed CloudWatch log-group ARN",
                )
            ],
            resources=[self._resource(name, "cloudwatch_logs.tf", content)],
            outputs=[
                self._output(
                    name,
                    "cloudwatch_logs_role_arn",
                    f"aws_iam_role.{resource}.arn",
                    "CloudTrail log-delivery role",
                )
            ],
        )
        result.merge(grants)
        return result

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        self._check_destination(connection, project)
        issues = external_service_key_issues(connection, project)
        trail = self._find_instance(connection.source_name, project)
        managed_bucket = any(
            item.source_name == trail.name
            and item.source_service == ServiceType.CLOUDTRAIL
            and item.target_service == ServiceType.S3
            and item.connection_type == "delivers_to"
            for item in project.connections
        )
        if not managed_bucket and not trail.config.s3_bucket_name:
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="CloudTrail still requires an S3 delivery bucket. Configure s3_bucket_name or connect a managed bucket with its delivery policy before applying.",
                )
            )
        return issues
