"""Neptune service generator — produces HCL for aws_neptune_cluster resources."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.neptune_config import (
    NEPTUNE_DATA_AUTH_VERSION_PATTERN,
    NeptuneConfig,
)
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> NeptuneConfig:
    """Resolve typed NeptuneConfig from the instance."""
    if isinstance(instance.config, NeptuneConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class NeptuneGenerator:
    """Generates Terraform files for Neptune clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_neptune_cluster resource."""
        config = _resolve_config(instance)
        attrs: dict = {"cluster_identifier": Expr("var.cluster_identifier")}
        if config.engine_version is not None:
            attrs["engine_version"] = Expr("var.engine_version")
        if config._iam_graph_access:
            attrs["iam_database_authentication_enabled"] = True
            pattern = self._r.render_expression(NEPTUNE_DATA_AUTH_VERSION_PATTERN)
            message = "Neptune graph IAM access requires engine 1.2.0.0 or newer."
            attrs["lifecycle"] = {
                "postcondition": {
                    "condition": Expr(f"can(regex({pattern}, self.engine_version))"),
                    "error_message": message,
                }
            }
            if config.engine_version is not None:
                attrs["lifecycle"]["precondition"] = {
                    "condition": Expr(f"can(regex({pattern}, var.engine_version))"),
                    "error_message": message,
                }

        return self._r.render_resource("aws_neptune_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Neptune cluster."""
        config = _resolve_config(instance)
        parts = [
            self._r.render_variable(
                "cluster_identifier", "string", "Identifier for the Neptune cluster"
            ),
        ]
        if config.engine_version is not None:
            parts.append(
                self._r.render_variable(
                    "engine_version",
                    "string",
                    "Neptune engine version",
                    default=config.engine_version,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Neptune cluster."""
        parts = [
            self._r.render_output(
                "cluster_arn",
                f"aws_neptune_cluster.{instance.name}.arn",
                "ARN of the Neptune cluster",
            ),
            self._r.render_output(
                "cluster_endpoint",
                f"aws_neptune_cluster.{instance.name}.endpoint",
                "Endpoint of the Neptune cluster",
            ),
        ]
        return "\n".join(parts)
