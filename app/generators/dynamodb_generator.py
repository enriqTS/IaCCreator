"""DynamoDB service generator — produces HCL for aws_dynamodb_table resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class DynamoDBGenerator:
    """Generates Terraform files for DynamoDB tables."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate dynamodb.tf with aws_dynamodb_table resource."""
        attrs: dict = {
            "name": "var.table_name",
            "billing_mode": "var.billing_mode",
            "hash_key": "var.hash_key",
        }

        # Build attribute blocks
        attribute_blocks = [
            {
                "name": instance.config.hash_key or "id",
                "type": instance.config.hash_key_type or "S",
            },
        ]

        if instance.config.range_key:
            attrs["range_key"] = "var.range_key"
            attribute_blocks.append(
                {
                    "name": instance.config.range_key,
                    "type": instance.config.range_key_type or "S",
                }
            )

        attrs["attribute"] = attribute_blocks

        # Capacity fields — only when billing_mode is PROVISIONED (visible_when)
        if instance.config.billing_mode == "PROVISIONED":
            if instance.config.read_capacity is not None:
                attrs["read_capacity"] = "var.read_capacity"
            if instance.config.write_capacity is not None:
                attrs["write_capacity"] = "var.write_capacity"

        if instance.config.table_class is not None:
            attrs["table_class"] = "var.table_class"
        if instance.config.deletion_protection_enabled is not None:
            attrs["deletion_protection_enabled"] = "var.deletion_protection_enabled"
        if instance.config.point_in_time_recovery_enabled is not None:
            attrs["point_in_time_recovery"] = {
                "enabled": "var.point_in_time_recovery_enabled"
            }
        if instance.config.tags is not None:
            attrs["tags"] = "var.tags"

        return self._r.render_resource("aws_dynamodb_table", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a DynamoDB instance."""
        parts = [
            self._r.render_variable(
                "table_name", "string", "Name of the DynamoDB table"
            ),
            self._r.render_variable(
                "billing_mode", "string", "Billing mode", default="PAY_PER_REQUEST"
            ),
            self._r.render_variable("hash_key", "string", "Hash key attribute name"),
        ]
        if instance.config.range_key:
            parts.append(
                self._r.render_variable(
                    "range_key", "string", "Range key attribute name"
                )
            )
        # Capacity variables — only when billing_mode is PROVISIONED (visible_when)
        if instance.config.billing_mode == "PROVISIONED":
            if instance.config.read_capacity is not None:
                parts.append(
                    self._r.render_variable(
                        "read_capacity",
                        "number",
                        "Provisioned read capacity units",
                        default=instance.config.read_capacity,
                    )
                )
            if instance.config.write_capacity is not None:
                parts.append(
                    self._r.render_variable(
                        "write_capacity",
                        "number",
                        "Provisioned write capacity units",
                        default=instance.config.write_capacity,
                    )
                )
        if instance.config.table_class is not None:
            parts.append(
                self._r.render_variable(
                    "table_class",
                    "string",
                    "Storage class for the DynamoDB table",
                    default=instance.config.table_class,
                )
            )
        if instance.config.deletion_protection_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "deletion_protection_enabled",
                    "bool",
                    "Enable deletion protection for the table",
                    default=instance.config.deletion_protection_enabled,
                )
            )
        if instance.config.point_in_time_recovery_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "point_in_time_recovery_enabled",
                    "bool",
                    "Enable point-in-time recovery for the table",
                    default=instance.config.point_in_time_recovery_enabled,
                )
            )
        if instance.config.tags is not None:
            parts.append(
                self._r.render_variable(
                    "tags",
                    "map(string)",
                    "Tags to apply to the DynamoDB table",
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a DynamoDB instance."""
        parts = [
            self._r.render_output(
                "table_arn",
                f"aws_dynamodb_table.{instance.name}.arn",
                "ARN of the DynamoDB table",
            ),
            self._r.render_output(
                "table_name",
                f"aws_dynamodb_table.{instance.name}.name",
                "Name of the DynamoDB table",
            ),
        ]
        return "\n".join(parts)
