"""Native private S3 origins with signed read-only CloudFront access."""

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.s3_bucket_policy import S3BucketPolicy


class CloudFrontS3Handler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="CloudFront serves GET/HEAD through a signed S3 REST origin. Upload content separately. External KMS keys require a distribution-scoped decrypt policy from the key owner.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        targets = {
            item.target_name
            for item in project.connections
            if item.source_name == connection.source_name
            and item.connection_type == "origin"
        }
        if len(targets) != 1:
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("origin",),
                        "msg": "The distribution model supports one managed S3 origin",
                    }
                ],
            )
        source = self._find_instance(connection.source_name, project)
        bucket = connection.target_name
        source.config._s3_origin = True
        source.config.origin_domain_name = "managed-by-connection"
        result = S3BucketPolicy().build(bucket, project)
        result.inputs.append(
            ModuleInput(
                module=source.name,
                name="origin_domain_name",
                value=f"module.{bucket}.bucket_regional_domain_name",
                description="Private S3 REST origin",
            )
        )
        result.outputs.append(
            ModuleOutput(
                module=bucket,
                name="bucket_regional_domain_name",
                value=f"aws_s3_bucket.{bucket}.bucket_regional_domain_name",
                description="Regional S3 REST endpoint",
            )
        )
        result.resources.append(
            self._resource(
                source.name,
                "origin_access.tf",
                self._renderer.render_resource(
                    "aws_cloudfront_origin_access_control",
                    "s3",
                    {
                        "name": f"{source.name}-s3",
                        "origin_access_control_origin_type": "s3",
                        "signing_behavior": "always",
                        "signing_protocol": "sigv4",
                    },
                ),
            )
        )
        return result
