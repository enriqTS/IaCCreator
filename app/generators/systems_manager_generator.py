from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.systems_manager_config import SystemsManagerConfig
from app.models.ir_models import ResourceInstanceIR


class SystemsManagerGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, SystemsManagerConfig)
        return self._r.render_resource(
            "aws_ssm_document",
            instance.name,
            {
                "name": Expr("var.document_name"),
                "document_type": Expr("var.document_type"),
                "document_format": Expr("var.document_format"),
                "content": Expr("var.content"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, SystemsManagerConfig)
        fields = [
            ("document_name", "string", "Document name"),
            ("document_type", "string", "Document type"),
            ("document_format", "string", "Document format"),
            ("content", "string", "Document body"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_ssm_document.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("document_arn", f"{ref}.arn", "Document ARN"),
                self._r.render_output("document_name", f"{ref}.name", "Document name"),
            ]
        )
