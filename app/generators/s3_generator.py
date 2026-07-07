"""S3 service generator — produces HCL for aws_s3_bucket resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class S3Generator:
    """Generates Terraform files for S3 buckets."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate s3.tf with aws_s3_bucket resource."""
        attrs: dict = {"bucket": "var.bucket_name"}
        if instance.config.force_destroy is not None:
            attrs["force_destroy"] = "var.force_destroy"
        if instance.config.object_lock_enabled is not None:
            attrs["object_lock_enabled"] = "var.object_lock_enabled"
        if instance.config.tags is not None:
            attrs["tags"] = "var.tags"

        result = self._r.render_resource("aws_s3_bucket", instance.name, attrs)

        versioning_attrs = {
            "bucket": f"aws_s3_bucket.{instance.name}.id",
            "versioning_configuration": {"status": "var.versioning_enabled"},
        }
        result += "\n" + self._r.render_resource(
            "aws_s3_bucket_versioning", f"{instance.name}_versioning", versioning_attrs
        )

        if instance.config.acceleration_status is not None:
            accel_attrs = {
                "bucket": f"aws_s3_bucket.{instance.name}.id",
                "status": "var.acceleration_status",
            }
            result += "\n" + self._r.render_resource(
                "aws_s3_bucket_accelerate_configuration",
                f"{instance.name}_accelerate",
                accel_attrs,
            )

        return result

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an S3 instance."""
        parts = [
            self._r.render_variable("bucket_name", "string", "Name of the S3 bucket"),
            self._r.render_variable(
                "versioning_enabled",
                "string",
                "Versioning status (Enabled or Suspended)",
                default="Enabled",
            ),
        ]
        if instance.config.force_destroy is not None:
            parts.append(
                self._r.render_variable(
                    "force_destroy",
                    "bool",
                    "Allow deletion of non-empty bucket by deleting all objects",
                    default=instance.config.force_destroy,
                )
            )
        if instance.config.object_lock_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "object_lock_enabled",
                    "bool",
                    "Enable S3 Object Lock on the bucket",
                    default=instance.config.object_lock_enabled,
                )
            )
        if instance.config.acceleration_status is not None:
            parts.append(
                self._r.render_variable(
                    "acceleration_status",
                    "string",
                    "Transfer acceleration status for the bucket",
                    default=instance.config.acceleration_status,
                )
            )
        if instance.config.tags is not None:
            parts.append(
                self._r.render_variable(
                    "tags",
                    "map(string)",
                    "Tags to apply to the S3 bucket",
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an S3 instance."""
        parts = [
            self._r.render_output(
                "bucket_arn",
                f"aws_s3_bucket.{instance.name}.arn",
                "ARN of the S3 bucket",
            ),
            self._r.render_output(
                "bucket_name",
                f"aws_s3_bucket.{instance.name}.id",
                "Name of the S3 bucket",
            ),
        ]
        return "\n".join(parts)
