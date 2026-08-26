"""Terraform generator for Amazon EFS file systems."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.efs_config import EfsConfig
from app.models.ir_models import ResourceInstanceIR


class EfsGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, EfsConfig)
        attrs = {
            "creation_token": instance.name,
            "encrypted": Expr("var.encrypted"),
            "performance_mode": Expr("var.performance_mode"),
            "throughput_mode": Expr("var.throughput_mode"),
        }
        if config.kms_key_id is not None:
            attrs["kms_key_id"] = Expr("var.kms_key_id")
        if config.throughput_mode == "provisioned":
            attrs["provisioned_throughput_in_mibps"] = Expr(
                "var.provisioned_throughput_in_mibps"
            )
        parts = [self._r.render_resource("aws_efs_file_system", instance.name, attrs)]
        if config.subnet_ids:
            parts.append(
                self._r.render_resource(
                    "aws_efs_mount_target",
                    instance.name,
                    {
                        "for_each": Expr("toset(var.subnet_ids)"),
                        "file_system_id": Expr(
                            f"aws_efs_file_system.{instance.name}.id"
                        ),
                        "subnet_id": Expr("each.value"),
                        "security_groups": Expr("var.security_group_ids"),
                    },
                )
            )
        return "\n".join(parts)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, EfsConfig)
        fields = [
            ("encrypted", "bool", "Encrypt data at rest"),
            ("performance_mode", "string", "File system performance mode"),
            ("throughput_mode", "string", "Throughput mode"),
            ("subnet_ids", "list(string)", "Mount target subnet IDs"),
            ("security_group_ids", "list(string)", "Mount target security group IDs"),
        ]
        if config.kms_key_id is not None:
            fields.append(("kms_key_id", "string", "KMS key ARN or ID"))
        if config.throughput_mode == "provisioned":
            fields.append(
                (
                    "provisioned_throughput_in_mibps",
                    "number",
                    "Provisioned throughput in MiB/s",
                )
            )
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_efs_file_system.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "file_system_id", f"{ref}.id", "EFS file system ID"
                ),
                self._r.render_output(
                    "file_system_arn", f"{ref}.arn", "EFS file system ARN"
                ),
                self._r.render_output("dns_name", f"{ref}.dns_name", "EFS DNS name"),
            ]
        )
