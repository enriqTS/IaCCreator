"""EC2 service generator — produces HCL for aws_instance resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.ec2_config import Ec2Config
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> Ec2Config:
    """Resolve typed Ec2Config, falling back to instance.config during migration."""
    if isinstance(instance.config, Ec2Config):
        return instance.config
    return instance.config  # type: ignore[return-value]


class EC2Generator:
    """Generates Terraform files for EC2 instances."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_instance resource."""
        config = _resolve_config(instance)

        attrs: dict = {
            "ami": "var.ami",
            "instance_type": "var.instance_type",
            "tags": {"Name": "var.instance_name"},
        }
        if config.key_name is not None:
            attrs["key_name"] = "var.key_name"

        return self._r.render_resource("aws_instance", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an EC2 instance."""
        config = _resolve_config(instance)

        parts = [
            self._r.render_variable(
                "instance_name", "string", "Name tag for the EC2 instance"
            ),
            self._r.render_variable("ami", "string", "AMI ID for the instance"),
            self._r.render_variable("instance_type", "string", "EC2 instance type"),
        ]
        if config.key_name is not None:
            parts.append(
                self._r.render_variable(
                    "key_name",
                    "string",
                    "Name of the SSH key pair",
                    default=config.key_name,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an EC2 instance."""
        parts = [
            self._r.render_output(
                "instance_id",
                f"aws_instance.{instance.name}.id",
                "ID of the EC2 instance",
            ),
            self._r.render_output(
                "public_ip",
                f"aws_instance.{instance.name}.public_ip",
                "Public IP address of the EC2 instance",
            ),
        ]
        return "\n".join(parts)
