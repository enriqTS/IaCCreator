"""Terraform generator for AWS Lake Formation resource registration."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.lake_formation_config import LakeFormationConfig
from app.models.ir_models import ResourceInstanceIR


class LakeFormationGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, LakeFormationConfig)
        attrs = {
            "arn": Expr("var.resource_arn"),
            "use_service_linked_role": Expr("var.use_service_linked_role"),
            "hybrid_access_enabled": Expr("var.hybrid_access_enabled"),
            "with_federation": Expr("var.with_federation"),
        }
        if config.role_arn is not None:
            attrs["role_arn"] = Expr("var.role_arn")
        return self._r.render_resource(
            "aws_lakeformation_resource", instance.name, attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, LakeFormationConfig)
        fields = [
            ("resource_arn", "string", "Registered S3 resource ARN"),
            ("use_service_linked_role", "bool", "Use the service-linked role"),
            ("hybrid_access_enabled", "bool", "Enable hybrid access"),
            ("with_federation", "bool", "Enable federated catalog access"),
        ]
        if config.role_arn is not None:
            fields.append(("role_arn", "string", "Resource access role ARN"))
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_lakeformation_resource.{instance.name}"
        return self._r.render_output(
            "resource_arn", f"{ref}.arn", "Registered resource ARN"
        )
