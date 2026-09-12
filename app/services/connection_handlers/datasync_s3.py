"""S3 transfer locations own scoped policies on their configured access roles."""

from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.datasync_location import DataSyncLocationHandler
from app.services.connection_handlers.kms_references import managed_key


class DataSyncS3Handler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The external access role must trust DataSync. Read locations receive source permissions; write locations can replace or delete destination objects when a task requests it. External key and cross-account bucket policies remain separately configured.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        source = self._find_instance(connection.source_name, project)
        buckets = {
            item.target_name
            for item in project.connections
            if item.source_name == source.name and item.connection_type == "uses_bucket"
        }
        if len(buckets) != 1 or not source.config.bucket_access_role_arn:
            DataSyncLocationHandler._reject(
                connection,
                "An S3 location requires one bucket and an external access role ARN",
            )
        bucket = connection.target_name
        source.config.s3_bucket_arn = "managed-by-connection"
        source.config._managed_bucket = True
        write = source.config.access == "write"
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source.name,
                    name="s3_bucket_arn",
                    value=f"module.{bucket}.bucket_arn",
                    description="Managed transfer bucket",
                )
            ]
        )
        objects = [
            "s3:GetObject",
            "s3:GetObjectVersion",
            "s3:GetObjectTagging",
            "s3:GetObjectVersionTagging",
        ]
        if write:
            objects += [
                "s3:PutObject",
                "s3:PutObjectTagging",
                "s3:DeleteObject",
                "s3:AbortMultipartUpload",
                "s3:ListMultipartUploadParts",
            ]
        statements = [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetBucketLocation",
                    "s3:ListBucket",
                    "s3:ListBucketMultipartUploads",
                ],
                "Resource": Expr("var.s3_bucket_arn"),
            },
            {
                "Effect": "Allow",
                "Action": objects,
                "Resource": Expr(
                    'format("%s/%s*", var.s3_bucket_arn, trimprefix(var.subdirectory, "/"))'
                ),
            },
        ]
        key = managed_key(bucket, project)
        if key:
            result.inputs.append(
                ModuleInput(
                    module=source.name,
                    name="location_key_arn",
                    value=f"module.{key}.key_arn",
                    description="Transfer object encryption key",
                )
            )
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey"]
                    if write
                    else ["kms:Decrypt"],
                    "Resource": Expr("var.location_key_arn"),
                }
            )
        result.resources.append(
            self._resource(
                source.name,
                "location_access.tf",
                self._renderer.render_resource(
                    "aws_iam_role_policy",
                    "location_access",
                    {
                        "name": f"{source.name}-location-access",
                        "role": Expr(
                            'element(reverse(split("/", var.bucket_access_role_arn)), 0)'
                        ),
                        "policy": self._renderer.render_json_policy(
                            {"Version": "2012-10-17", "Statement": statements}
                        ),
                    },
                ),
            )
        )
        return result
