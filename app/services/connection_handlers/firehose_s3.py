"""Firehose owns its S3 destination configuration and delivery-role policy."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.storage import S3LocationConfig
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_references import managed_key


class FirehoseS3Handler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The external delivery role must trust Firehose. This connection grants destination S3 access and managed-key permissions; stream producers and external-key policies remain separately configured.",
            )
        ]

    @staticmethod
    def _reject(connection: ConnectionIR, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": ("destination",), "msg": message}],
        )

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        source = self._find_instance(connection.source_name, project)
        locations = {
            (
                item.target_name,
                S3LocationConfig.model_validate(item.connection_config).prefix,
            )
            for item in project.connections
            if item.source_name == source.name
            and item.connection_type == connection.connection_type
        }
        if len(locations) != 1:
            self._reject(connection, "Firehose supports one managed S3 destination")
        if not source.config.role_arn:
            self._reject(connection, "Firehose requires an external delivery role ARN")
        if source.config.destination not in {None, "s3", "extended_s3"}:
            self._reject(
                connection,
                "The S3 destination connection requires an extended_s3 stream",
            )
        bucket, prefix = next(iter(locations))
        source.config.destination = "extended_s3"
        source.config.bucket_arn = "managed-by-connection"
        source.config._managed_s3_destination = True
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source.name,
                    name="destination",
                    value='"extended_s3"',
                    description="Native S3 delivery",
                ),
                ModuleInput(
                    module=source.name,
                    name="bucket_arn",
                    value=f"module.{bucket}.bucket_arn",
                    description="Managed delivery bucket",
                ),
                ModuleInput(
                    module=source.name,
                    name="s3_prefix",
                    value=self._renderer.render_expression(prefix),
                    description="Delivery object prefix",
                ),
            ]
        )
        statements = [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetBucketLocation",
                    "s3:ListBucket",
                    "s3:ListBucketMultipartUploads",
                ],
                "Resource": Expr("var.bucket_arn"),
            },
            {
                "Effect": "Allow",
                "Action": ["s3:AbortMultipartUpload", "s3:GetObject", "s3:PutObject"],
                "Resource": Expr('format("%s/%s*", var.bucket_arn, var.s3_prefix)'),
            },
        ]
        key = managed_key(bucket, project)
        if key:
            result.inputs.append(
                ModuleInput(
                    module=source.name,
                    name="delivery_key_arn",
                    value=f"module.{key}.key_arn",
                    description="Delivery bucket encryption key",
                )
            )
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
                    "Resource": Expr("var.delivery_key_arn"),
                }
            )
        result.resources.append(
            self._resource(
                source.name,
                "delivery_policy.tf",
                self._renderer.render_resource(
                    "aws_iam_role_policy",
                    "s3_delivery",
                    {
                        "name": f"{source.name}-s3-delivery",
                        "role": Expr('element(reverse(split("/", var.role_arn)), 0)'),
                        "policy": self._renderer.render_json_policy(
                            {"Version": "2012-10-17", "Statement": statements}
                        ),
                    },
                ),
            )
        )
        return result
