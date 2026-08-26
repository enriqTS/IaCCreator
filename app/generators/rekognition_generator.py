from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.rekognition_config import RekognitionConfig
from app.models.ir_models import ResourceInstanceIR


class RekognitionGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, RekognitionConfig)
        return self._r.render_resource(
            "aws_rekognition_collection",
            instance.name,
            {
                "collection_id": Expr("var.collection_id"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, RekognitionConfig)
        fields = [
            ("collection_id", "string", "Collection identifier"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_rekognition_collection.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("collection_arn", f"{ref}.arn", "Collection ARN"),
                self._r.render_output(
                    "collection_id", f"{ref}.collection_id", "Collection identifier"
                ),
            ]
        )
