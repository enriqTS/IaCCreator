"""Terraform generator for AWS DMS replication instances."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.dms_config import DmsConfig
from app.models.ir_models import ResourceInstanceIR


class DmsGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, DmsConfig)
        parts = []
        if config.subnet_ids:
            parts.append(
                self._r.render_resource(
                    "aws_dms_replication_subnet_group",
                    instance.name,
                    {
                        "replication_subnet_group_description": f"Subnet group for {instance.name}",
                        "replication_subnet_group_id": f"{instance.name.replace('_', '-')}-subnets",
                        "subnet_ids": Expr("var.subnet_ids"),
                    },
                )
            )
        attrs = {
            "replication_instance_id": Expr("var.replication_instance_id"),
            "replication_instance_class": Expr("var.replication_instance_class"),
            "allocated_storage": Expr("var.allocated_storage"),
            "multi_az": Expr("var.multi_az"),
            "publicly_accessible": Expr("var.publicly_accessible"),
            "vpc_security_group_ids": Expr("var.vpc_security_group_ids"),
            "auto_minor_version_upgrade": Expr("var.auto_minor_version_upgrade"),
        }
        if config.engine_version is not None:
            attrs["engine_version"] = Expr("var.engine_version")
        if config.subnet_ids:
            attrs["replication_subnet_group_id"] = Expr(
                f"aws_dms_replication_subnet_group.{instance.name}.id"
            )
        parts.append(
            self._r.render_resource(
                "aws_dms_replication_instance", instance.name, attrs
            )
        )
        return "\n".join(parts)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, DmsConfig)
        fields = [
            ("replication_instance_id", "string", "Replication instance identifier"),
            ("replication_instance_class", "string", "Replication instance class"),
            ("allocated_storage", "number", "Allocated storage in GiB"),
            ("multi_az", "bool", "Enable Multi-AZ"),
            ("publicly_accessible", "bool", "Assign a public IP address"),
            ("subnet_ids", "list(string)", "Replication subnet IDs"),
            (
                "vpc_security_group_ids",
                "list(string)",
                "Replication instance security groups",
            ),
            ("auto_minor_version_upgrade", "bool", "Install minor engine upgrades"),
        ]
        if config.engine_version is not None:
            fields.append(("engine_version", "string", "DMS engine version"))
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_dms_replication_instance.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "replication_instance_arn",
                    f"{ref}.replication_instance_arn",
                    "Replication instance ARN",
                ),
                self._r.render_output(
                    "replication_instance_id",
                    f"{ref}.replication_instance_id",
                    "Replication instance ID",
                ),
            ]
        )
