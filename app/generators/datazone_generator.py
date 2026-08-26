"""Terraform generator for Amazon DataZone domains."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.datazone_config import DataZoneConfig
from app.models.ir_models import ResourceInstanceIR


class DataZoneGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, DataZoneConfig)
        attrs = {
            "name": Expr("var.domain_name"),
            "domain_execution_role": Expr("var.domain_execution_role"),
        }
        if config.description is not None:
            attrs["description"] = Expr("var.description")
        if config.kms_key_identifier is not None:
            attrs["kms_key_identifier"] = Expr("var.kms_key_identifier")
        return self._r.render_resource("aws_datazone_domain", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, DataZoneConfig)
        fields = [
            ("domain_name", "string", "DataZone domain name"),
            ("domain_execution_role", "string", "Domain execution role ARN"),
        ]
        if config.description is not None:
            fields.append(("description", "string", "Domain description"))
        if config.kms_key_identifier is not None:
            fields.append(("kms_key_identifier", "string", "Domain KMS key"))
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_datazone_domain.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("domain_id", f"{ref}.id", "DataZone domain ID"),
                self._r.render_output(
                    "domain_arn", f"{ref}.arn", "DataZone domain ARN"
                ),
                self._r.render_output(
                    "portal_url", f"{ref}.portal_url", "DataZone portal URL"
                ),
            ]
        )
