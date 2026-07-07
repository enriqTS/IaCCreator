"""Connect service generator — produces HCL for aws_connect_instance resources."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.connect_config import ConnectConfig
from app.models.ir_models import ResourceInstanceIR


class ConnectGenerator:
    """Generates Terraform files for Connect instances."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_connect_instance resource."""
        config = get_typed_config(instance, ConnectConfig)

        attrs: dict = {}
        if config.identity_management_type is not None:
            attrs["identity_management_type"] = "var.identity_management_type"
        if config.inbound_calls_enabled is not None:
            attrs["inbound_calls_enabled"] = "var.inbound_calls_enabled"
        if config.outbound_calls_enabled is not None:
            attrs["outbound_calls_enabled"] = "var.outbound_calls_enabled"

        return self._r.render_resource("aws_connect_instance", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Connect instance."""
        config = get_typed_config(instance, ConnectConfig)

        parts = []
        if config.identity_management_type is not None:
            parts.append(
                self._r.render_variable(
                    "identity_management_type",
                    "string",
                    "Identity management type for the Connect instance",
                    default=config.identity_management_type,
                )
            )
        if config.inbound_calls_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "inbound_calls_enabled",
                    "bool",
                    "Whether inbound calls are enabled",
                    default=config.inbound_calls_enabled,
                )
            )
        if config.outbound_calls_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "outbound_calls_enabled",
                    "bool",
                    "Whether outbound calls are enabled",
                    default=config.outbound_calls_enabled,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Connect instance."""
        parts = [
            self._r.render_output(
                "instance_id",
                f"aws_connect_instance.{instance.name}.id",
                "ID of the Connect instance",
            ),
            self._r.render_output(
                "instance_arn",
                f"aws_connect_instance.{instance.name}.arn",
                "ARN of the Connect instance",
            ),
        ]
        return "\n".join(parts)
