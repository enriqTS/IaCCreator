"""Compose service permissions into one policy owned by each bucket."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionContribution, ModuleOutput, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.s3_audit_policy import S3AuditPolicy
from app.services.connection_handlers.s3_origin_policy import S3OriginPolicy


class S3BucketPolicy(BaseConnectionHandler):
    def build(self, bucket: str, project: ProjectIR) -> ConnectionContribution:
        result = ConnectionContribution()
        statements = []
        for builder in (S3AuditPolicy(), S3OriginPolicy()):
            additions, contribution = builder.build(bucket, project)
            statements.extend(additions)
            result.merge(contribution)
        resource = f"{bucket}_delivery"
        result.resources.append(
            self._resource(
                bucket,
                "bucket_policy.tf",
                self._renderer.render_resource(
                    "aws_s3_bucket_policy",
                    resource,
                    {
                        "bucket": Expr(f"aws_s3_bucket.{bucket}.id"),
                        "policy": self._renderer.render_json_policy(
                            {"Version": "2012-10-17", "Statement": statements}
                        ),
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
