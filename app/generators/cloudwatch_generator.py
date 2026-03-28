"""CloudWatch service generator — produces HCL for aws_cloudwatch_log_group resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class CloudWatchGenerator:
    """Generates Terraform files for CloudWatch log group resources."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate cloudwatch.tf with aws_cloudwatch_log_group resource."""
        attrs: dict = {"name": "var.log_group_name"}
        if instance.config.retention_in_days is not None:
            attrs["retention_in_days"] = "var.retention_in_days"
        if instance.config.kms_key_id is not None:
            attrs["kms_key_id"] = "var.kms_key_id"
        if instance.config.log_group_class is not None:
            attrs["log_group_class"] = "var.log_group_class"
        if instance.config.tags is not None:
            attrs["tags"] = "var.tags"
        return self._r.render_resource("aws_cloudwatch_log_group", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a CloudWatch instance."""
        parts = [
            self._r.render_variable("log_group_name", "string", "Name of the CloudWatch log group"),
        ]
        if instance.config.retention_in_days is not None:
            parts.append(self._r.render_variable(
                "retention_in_days", "number", "Log retention period in days",
                default=instance.config.retention_in_days,
            ))
        if instance.config.kms_key_id is not None:
            parts.append(self._r.render_variable(
                "kms_key_id", "string", "ARN of the KMS key to use for encrypting log data",
                default=instance.config.kms_key_id,
            ))
        if instance.config.log_group_class is not None:
            parts.append(self._r.render_variable(
                "log_group_class", "string", "Log group class for the CloudWatch log group",
                default=instance.config.log_group_class,
            ))
        if instance.config.tags is not None:
            parts.append(self._r.render_variable(
                "tags", "map(string)", "Tags to apply to the CloudWatch log group",
            ))
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a CloudWatch instance."""
        return self._r.render_output(
            "log_group_arn",
            f"aws_cloudwatch_log_group.{instance.name}.arn",
            "ARN of the CloudWatch log group",
        )
