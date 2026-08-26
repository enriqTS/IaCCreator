"""Terraform generator for Amazon Keyspaces keyspaces."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.keyspaces_config import KeyspacesConfig
from app.models.ir_models import ResourceInstanceIR


class KeyspacesGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, KeyspacesConfig)
        return self._r.render_resource(
            "aws_keyspaces_keyspace",
            instance.name,
            {
                "name": Expr("var.keyspace_name"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, KeyspacesConfig)
        return self._r.render_variable("keyspace_name", "string", "Keyspace name")

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_keyspaces_keyspace.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("keyspace_id", f"{ref}.id", "Keyspace ID"),
                self._r.render_output("keyspace_arn", f"{ref}.arn", "Keyspace ARN"),
            ]
        )
