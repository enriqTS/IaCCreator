"""DynamoDB service generator — produces HCL for aws_dynamodb_table resources."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.dynamodb_config import DynamoDBConfig
from app.models.ir_models import ResourceInstanceIR


class DynamoDBGenerator:
    """Generates Terraform files for DynamoDB tables."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate dynamodb.tf with aws_dynamodb_table resource."""
        config = get_typed_config(instance, DynamoDBConfig)

        attrs: dict = {
            "name": "var.table_name",
            "billing_mode": "var.billing_mode",
            "hash_key": "var.hash_key",
        }

        # Build attribute blocks
        attribute_blocks = [
            {
                "name": config.hash_key or "id",
                "type": config.hash_key_type or "S",
            },
        ]

        if config.range_key:
            attrs["range_key"] = "var.range_key"
            attribute_blocks.append(
                {
                    "name": config.range_key,
                    "type": config.range_key_type or "S",
                }
            )

        attrs["attribute"] = attribute_blocks

        # Capacity fields — only when billing_mode is PROVISIONED (visible_when)
        if config.billing_mode == "PROVISIONED":
            if config.read_capacity is not None:
                attrs["read_capacity"] = "var.read_capacity"
            if config.write_capacity is not None:
                attrs["write_capacity"] = "var.write_capacity"

        if config.table_class is not None:
            attrs["table_class"] = "var.table_class"
        if config.deletion_protection_enabled is not None:
            attrs["deletion_protection_enabled"] = "var.deletion_protection_enabled"
        if config.point_in_time_recovery_enabled is not None:
            attrs["point_in_time_recovery"] = {
                "enabled": "var.point_in_time_recovery_enabled"
            }
        if config.tags is not None:
            attrs["tags"] = "var.tags"

        # Stream attributes (Requirement 3.11)
        if config.stream_enabled is not None:
            attrs["stream_enabled"] = "var.stream_enabled"
        if config.stream_view_type is not None:
            attrs["stream_view_type"] = "var.stream_view_type"

        # TTL nested block (Requirement 3.12)
        if config.ttl_enabled is not None:
            ttl_block: dict = {"enabled": "var.ttl_enabled"}
            if config.ttl_attribute_name is not None:
                ttl_block["attribute_name"] = "var.ttl_attribute_name"
            attrs["ttl"] = ttl_block

        # Global Secondary Index repeated blocks (Requirement 3.13)
        if config.global_secondary_indexes is not None:
            gsi_blocks = []
            for gsi in config.global_secondary_indexes:
                gsi_block: dict = {
                    "name": gsi["name"],
                    "hash_key": gsi["hash_key"],
                    "projection_type": gsi.get("projection_type", "ALL"),
                }
                if "range_key" in gsi and gsi["range_key"] is not None:
                    gsi_block["range_key"] = gsi["range_key"]
                if "read_capacity" in gsi and gsi["read_capacity"] is not None:
                    gsi_block["read_capacity"] = gsi["read_capacity"]
                if "write_capacity" in gsi and gsi["write_capacity"] is not None:
                    gsi_block["write_capacity"] = gsi["write_capacity"]
                if (
                    "non_key_attributes" in gsi
                    and gsi["non_key_attributes"] is not None
                ):
                    gsi_block["non_key_attributes"] = gsi["non_key_attributes"]
                gsi_blocks.append(gsi_block)
            attrs["global_secondary_index"] = gsi_blocks

        # Local Secondary Index repeated blocks (Requirement 3.13)
        if config.local_secondary_indexes is not None:
            lsi_blocks = []
            for lsi in config.local_secondary_indexes:
                lsi_block: dict = {
                    "name": lsi["name"],
                    "range_key": lsi["range_key"],
                    "projection_type": lsi.get("projection_type", "ALL"),
                }
                if (
                    "non_key_attributes" in lsi
                    and lsi["non_key_attributes"] is not None
                ):
                    lsi_block["non_key_attributes"] = lsi["non_key_attributes"]
                lsi_blocks.append(lsi_block)
            attrs["local_secondary_index"] = lsi_blocks

        # Server-side encryption nested block (Requirement 3.14)
        if config.server_side_encryption_enabled is not None:
            sse_block: dict = {"enabled": "var.server_side_encryption_enabled"}
            if config.server_side_encryption_kms_key_arn is not None:
                sse_block["kms_key_arn"] = "var.server_side_encryption_kms_key_arn"
            attrs["server_side_encryption"] = sse_block

        # Replica repeated blocks (Requirement 3.15)
        if config.replica_regions is not None:
            replica_blocks = []
            for region in config.replica_regions:
                replica_blocks.append({"region_name": region})
            attrs["replica"] = replica_blocks

        # On-demand capacity limits (PAY_PER_REQUEST mode)
        if config.billing_mode == "PAY_PER_REQUEST":
            if (
                config.on_demand_max_read_request_units is not None
                or config.on_demand_max_write_request_units is not None
            ):
                on_demand_block: dict = {}
                if config.on_demand_max_read_request_units is not None:
                    on_demand_block["max_read_request_units"] = (
                        "var.on_demand_max_read_request_units"
                    )
                if config.on_demand_max_write_request_units is not None:
                    on_demand_block["max_write_request_units"] = (
                        "var.on_demand_max_write_request_units"
                    )
                attrs["on_demand_throughput"] = on_demand_block

        return self._r.render_resource("aws_dynamodb_table", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a DynamoDB instance."""
        config = get_typed_config(instance, DynamoDBConfig)

        # Required fields — no default (Requirements 5.6, 6.6)
        parts = [
            self._r.render_variable(
                "table_name", "string", "Name of the DynamoDB table"
            ),
            self._r.render_variable("hash_key", "string", "Hash key attribute name"),
            self._r.render_variable(
                "hash_key_type", "string", "Hash key attribute type"
            ),
        ]

        # billing_mode — optional with default
        parts.append(
            self._r.render_variable(
                "billing_mode", "string", "Billing mode", default="PAY_PER_REQUEST"
            )
        )

        if config.range_key:
            parts.append(
                self._r.render_variable(
                    "range_key", "string", "Range key attribute name"
                )
            )

        # Capacity variables — only when billing_mode is PROVISIONED (visible_when)
        if config.billing_mode == "PROVISIONED":
            if config.read_capacity is not None:
                parts.append(
                    self._r.render_variable(
                        "read_capacity",
                        "number",
                        "Provisioned read capacity units",
                        default=config.read_capacity,
                    )
                )
            if config.write_capacity is not None:
                parts.append(
                    self._r.render_variable(
                        "write_capacity",
                        "number",
                        "Provisioned write capacity units",
                        default=config.write_capacity,
                    )
                )

        if config.table_class is not None:
            parts.append(
                self._r.render_variable(
                    "table_class",
                    "string",
                    "Storage class for the DynamoDB table",
                    default=config.table_class,
                )
            )
        if config.deletion_protection_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "deletion_protection_enabled",
                    "bool",
                    "Enable deletion protection for the table",
                    default=config.deletion_protection_enabled,
                )
            )
        if config.point_in_time_recovery_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "point_in_time_recovery_enabled",
                    "bool",
                    "Enable point-in-time recovery for the table",
                    default=config.point_in_time_recovery_enabled,
                )
            )
        if config.tags is not None:
            parts.append(
                self._r.render_variable(
                    "tags",
                    "map(string)",
                    "Tags to apply to the DynamoDB table",
                )
            )

        # Stream variables (Requirement 3.11)
        if config.stream_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "stream_enabled",
                    "bool",
                    "Enable DynamoDB Streams on the table",
                    default=config.stream_enabled,
                )
            )
        if config.stream_view_type is not None:
            parts.append(
                self._r.render_variable(
                    "stream_view_type",
                    "string",
                    "Type of information written to the stream",
                    default=config.stream_view_type,
                )
            )

        # TTL variables (Requirement 3.12)
        if config.ttl_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "ttl_enabled",
                    "bool",
                    "Enable Time to Live (TTL) for the table",
                    default=config.ttl_enabled,
                )
            )
        if config.ttl_attribute_name is not None:
            parts.append(
                self._r.render_variable(
                    "ttl_attribute_name",
                    "string",
                    "Name of the TTL attribute",
                    default=config.ttl_attribute_name,
                )
            )

        # Index variables (Requirement 5.3 — use type "any" for complex list[dict])
        if config.global_secondary_indexes is not None:
            parts.append(
                self._r.render_variable(
                    "global_secondary_indexes",
                    "any",
                    "List of global secondary index definitions",
                    default=config.global_secondary_indexes,
                )
            )
        if config.local_secondary_indexes is not None:
            parts.append(
                self._r.render_variable(
                    "local_secondary_indexes",
                    "any",
                    "List of local secondary index definitions",
                    default=config.local_secondary_indexes,
                )
            )

        # Encryption variables (Requirement 3.14)
        if config.server_side_encryption_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "server_side_encryption_enabled",
                    "bool",
                    "Enable server-side encryption with a KMS key",
                    default=config.server_side_encryption_enabled,
                )
            )
        if config.server_side_encryption_kms_key_arn is not None:
            parts.append(
                self._r.render_variable(
                    "server_side_encryption_kms_key_arn",
                    "string",
                    "ARN of the KMS key for server-side encryption",
                    default=config.server_side_encryption_kms_key_arn,
                )
            )

        # Replica variables (Requirement 3.15)
        if config.replica_regions is not None:
            parts.append(
                self._r.render_variable(
                    "replica_regions",
                    "list(string)",
                    "List of regions for global table replicas",
                    default=config.replica_regions,
                )
            )

        # On-demand capacity limit variables
        if config.billing_mode == "PAY_PER_REQUEST":
            if config.on_demand_max_read_request_units is not None:
                parts.append(
                    self._r.render_variable(
                        "on_demand_max_read_request_units",
                        "number",
                        "Maximum read request units for on-demand capacity mode",
                        default=config.on_demand_max_read_request_units,
                    )
                )
            if config.on_demand_max_write_request_units is not None:
                parts.append(
                    self._r.render_variable(
                        "on_demand_max_write_request_units",
                        "number",
                        "Maximum write request units for on-demand capacity mode",
                        default=config.on_demand_max_write_request_units,
                    )
                )

        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a DynamoDB instance."""
        config = get_typed_config(instance, DynamoDBConfig)  # noqa: F841

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
