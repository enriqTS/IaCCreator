"""Athena service generator — produces HCL for aws_athena_workgroup resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.athena_config import AthenaConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> AthenaConfig:
    """Resolve typed AthenaConfig, falling back to instance.config during migration."""
    if isinstance(instance.config, AthenaConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class AthenaGenerator:
    """Generates Terraform files for Athena workgroups."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_athena_workgroup resource."""
        config = _resolve_config(instance)
        attrs: dict = {"name": Expr("var.workgroup_name")}
        if config.output_location is not None:
            attrs["configuration"] = {
                "enforce_workgroup_configuration": Expr(
                    "var.enforce_workgroup_configuration"
                ),
                "result_configuration": {
                    "output_location": Expr("var.output_location")
                },
            }

        return self._r.render_resource("aws_athena_workgroup", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an Athena workgroup."""
        parts = [
            self._r.render_variable(
                "workgroup_name", "string", "Name of the Athena workgroup"
            ),
        ]
        config = _resolve_config(instance)
        if config.output_location is not None:
            parts.extend(
                [
                    self._r.render_variable(
                        "output_location",
                        "string",
                        "S3 query result location",
                        default=config.output_location,
                    ),
                    self._r.render_variable(
                        "enforce_workgroup_configuration",
                        "bool",
                        "Enforce workgroup result configuration",
                        default=config.enforce_workgroup_configuration,
                    ),
                ]
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an Athena workgroup."""
        parts = [
            self._r.render_output(
                "workgroup_arn",
                f"aws_athena_workgroup.{instance.name}.arn",
                "ARN of the Athena workgroup",
            ),
            self._r.render_output(
                "workgroup_name",
                f"aws_athena_workgroup.{instance.name}.name",
                "Name of the Athena workgroup",
            ),
        ]
        return "\n".join(parts)
