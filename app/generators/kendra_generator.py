from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.kendra_config import KendraConfig
from app.models.ir_models import ResourceInstanceIR


class KendraGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, KendraConfig)
        return self._r.render_resource(
            "aws_kendra_index",
            instance.name,
            {
                "name": Expr("var.index_name"),
                "role_arn": Expr("var.role_arn"),
                "edition": Expr("var.edition"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, KendraConfig)
        fields = [
            ("index_name", "string", "Index name"),
            ("role_arn", "string", "Kendra role ARN"),
            ("edition", "string", "Index edition"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_kendra_index.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("index_id", f"{ref}.id", "Index ID"),
                self._r.render_output("index_arn", f"{ref}.arn", "Index ARN"),
            ]
        )
