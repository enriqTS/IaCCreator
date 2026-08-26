"""Terraform generator for Amazon EBS volumes."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.ebs_config import EbsConfig
from app.models.ir_models import ResourceInstanceIR


class EbsGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, EbsConfig)
        attrs = {
            "availability_zone": Expr("var.availability_zone"),
            "size": Expr("var.size"),
            "type": Expr("var.volume_type"),
            "encrypted": Expr("var.encrypted"),
        }
        if config.volume_type in {"gp3", "io1", "io2"}:
            attrs["iops"] = Expr("var.iops")
        if config.volume_type == "gp3":
            attrs["throughput"] = Expr("var.throughput")
        if config.kms_key_id is not None:
            attrs["kms_key_id"] = Expr("var.kms_key_id")
        if config.snapshot_id is not None:
            attrs["snapshot_id"] = Expr("var.snapshot_id")
        return self._r.render_resource("aws_ebs_volume", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, EbsConfig)
        fields = [
            ("availability_zone", "string", "Volume Availability Zone"),
            ("size", "number", "Volume size in GiB"),
            ("volume_type", "string", "EBS volume type"),
            ("encrypted", "bool", "Encrypt the volume"),
        ]
        if config.volume_type in {"gp3", "io1", "io2"}:
            fields.append(("iops", "number", "Provisioned IOPS"))
        if config.volume_type == "gp3":
            fields.append(("throughput", "number", "Throughput in MiB/s"))
        if config.kms_key_id is not None:
            fields.append(("kms_key_id", "string", "KMS key ARN or ID"))
        if config.snapshot_id is not None:
            fields.append(("snapshot_id", "string", "Source snapshot ID"))
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_ebs_volume.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("volume_id", f"{ref}.id", "EBS volume ID"),
                self._r.render_output("volume_arn", f"{ref}.arn", "EBS volume ARN"),
            ]
        )
