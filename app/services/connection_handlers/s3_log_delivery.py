"""Aggregate audit-service delivery permissions in one bucket-owned policy."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_identities import identity

DELIVERY_SERVICES = {ServiceType.CLOUDTRAIL, ServiceType.AWS_CONFIG}


class S3LogDeliveryHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Delivery uses a bucket-owned service policy. AWS Config still requires its configured recorder role and recording permissions. KMS-encrypted delivery requires appropriate service/role key permissions; configure those separately.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        peers = [
            item
            for item in project.connections
            if item.source_service in DELIVERY_SERVICES
            and item.target_service == ServiceType.S3
            and item.connection_type == "delivers_to"
        ]
        for source in {item.source_name for item in peers}:
            if (
                len({item.target_name for item in peers if item.source_name == source})
                > 1
            ):
                raise InvalidConnectionConfigError(
                    source,
                    connection.target_name,
                    connection.connection_type,
                    [
                        {
                            "loc": ("target",),
                            "msg": "An audit service supports one managed delivery bucket",
                        }
                    ],
                )
        bucket = connection.target_name
        sources = sorted(
            {item.source_name for item in peers if item.target_name == bucket}
        )
        result = ConnectionContribution()
        statements = []
        for name in sources:
            source = self._find_instance(name, project)
            source.config.s3_bucket_name = "managed-by-connection"
            account_var = f"delivery_{name}_account"
            result.resources.append(
                self._resource(
                    name,
                    "delivery_identity.tf",
                    'data "aws_caller_identity" "delivery" {}\n',
                )
            )
            result.outputs.append(
                ModuleOutput(
                    module=name,
                    name="delivery_account_id",
                    value="data.aws_caller_identity.delivery.account_id",
                    description="Delivery account independent of service creation",
                )
            )
            result.inputs.extend(
                [
                    ModuleInput(
                        module=bucket,
                        name=account_var,
                        value=f"module.{name}.delivery_account_id",
                        description="Account permitted to deliver logs",
                    ),
                    ModuleInput(
                        module=name,
                        name="s3_bucket_name",
                        value=f"module.{bucket}.delivery_bucket_name",
                        description="Bucket available after delivery policy creation",
                    ),
                ]
            )
            is_trail = source.service_type == ServiceType.CLOUDTRAIL
            conditions = {"aws:SourceAccount": Expr(f"var.{account_var}")}
            if is_trail:
                trail_arn, contribution = identity(source)
                result.inputs.extend(contribution.inputs)
                result.outputs.extend(contribution.outputs)
                result.resources.extend(contribution.resources)
                trail_var = f"delivery_{name}_trail_arn"
                result.inputs.append(
                    ModuleInput(
                        module=bucket,
                        name=trail_var,
                        value=trail_arn,
                        description="Trail identity independent of creation",
                    )
                )
                conditions["aws:SourceArn"] = Expr(f"var.{trail_var}")
            principal = {
                "Service": "cloudtrail.amazonaws.com"
                if is_trail
                else "config.amazonaws.com"
            }
            statements.append(
                {
                    "Effect": "Allow",
                    "Principal": principal,
                    "Action": ["s3:GetBucketAcl"]
                    if is_trail
                    else ["s3:GetBucketAcl", "s3:ListBucket"],
                    "Resource": Expr(f"aws_s3_bucket.{bucket}.arn"),
                    "Condition": {"StringEquals": conditions},
                }
            )
            suffix = "*" if is_trail else "Config/*"
            statements.append(
                {
                    "Effect": "Allow",
                    "Principal": principal,
                    "Action": "s3:PutObject",
                    "Resource": Expr(
                        f'"${{aws_s3_bucket.{bucket}.arn}}/AWSLogs/${{var.{account_var}}}/{suffix}"'
                    ),
                    "Condition": {
                        "StringEquals": {
                            **conditions,
                            "s3:x-amz-acl": "bucket-owner-full-control",
                        }
                    },
                }
            )
        resource = f"{bucket}_delivery"
        policy = self._renderer.render_expression(
            {"Version": "2012-10-17", "Statement": statements}
        )
        result.resources.append(
            self._resource(
                bucket,
                "bucket_policy.tf",
                self._renderer.render_resource(
                    "aws_s3_bucket_policy",
                    resource,
                    {
                        "bucket": Expr(f"aws_s3_bucket.{bucket}.id"),
                        "policy": Expr(f"jsonencode({policy})"),
                    },
                ),
            )
        )
        result.outputs.append(
            ModuleOutput(
                module=bucket,
                name="delivery_bucket_name",
                value=f"aws_s3_bucket.{bucket}.id",
                description="Bucket ready for audit delivery",
                depends_on=[f"aws_s3_bucket_policy.{resource}"],
            )
        )
        return result
