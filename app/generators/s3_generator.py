"""S3 service generator — produces HCL for aws_s3_bucket resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.s3_config import S3Config
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> S3Config:
    """Resolve typed S3Config from instance config.

    Falls back to duck-typed access if field names match.
    """
    if isinstance(instance.config, S3Config):
        return instance.config
    # Fallback: duck-typed access works if field names match
    return instance.config  # type: ignore[return-value]


class S3Generator:
    """Generates Terraform files for S3 buckets."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate s3.tf with aws_s3_bucket resource."""
        config = _resolve_config(instance)

        attrs: dict = {"bucket": "var.bucket_name"}
        if config.force_destroy is not None:
            attrs["force_destroy"] = "var.force_destroy"
        if config.object_lock_enabled is not None:
            attrs["object_lock_enabled"] = "var.object_lock_enabled"
        if config.tags is not None:
            attrs["tags"] = "var.tags"

        result = self._r.render_resource("aws_s3_bucket", instance.name, attrs)

        versioning_attrs = {
            "bucket": f"aws_s3_bucket.{instance.name}.id",
            "versioning_configuration": {"status": "var.versioning_enabled"},
        }
        result += "\n" + self._r.render_resource(
            "aws_s3_bucket_versioning", f"{instance.name}_versioning", versioning_attrs
        )

        if config.acceleration_status is not None:
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
        config = _resolve_config(instance)

        parts = [
            self._r.render_variable("bucket_name", "string", "Name of the S3 bucket"),
            self._r.render_variable(
                "versioning_enabled",
                "string",
                "Versioning status (Enabled or Suspended)",
                default="Enabled",
            ),
        ]
        if config.force_destroy is not None:
            parts.append(
                self._r.render_variable(
                    "force_destroy",
                    "bool",
                    "Allow deletion of non-empty bucket by deleting all objects",
                    default=config.force_destroy,
                )
            )
        if config.object_lock_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "object_lock_enabled",
                    "bool",
                    "Enable S3 Object Lock on the bucket",
                    default=config.object_lock_enabled,
                )
            )
        if config.acceleration_status is not None:
            parts.append(
                self._r.render_variable(
                    "acceleration_status",
                    "string",
                    "Transfer acceleration status for the bucket",
                    default=config.acceleration_status,
                )
            )
        if config.tags is not None:
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
