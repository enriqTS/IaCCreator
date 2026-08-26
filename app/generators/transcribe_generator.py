from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.transcribe_config import TranscribeConfig
from app.models.ir_models import ResourceInstanceIR


class TranscribeGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, TranscribeConfig)
        return self._r.render_resource(
            "aws_transcribe_vocabulary",
            instance.name,
            {
                "vocabulary_name": Expr("var.vocabulary_name"),
                "language_code": Expr("var.language_code"),
                "phrases": Expr("var.phrases"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, TranscribeConfig)
        fields = [
            ("vocabulary_name", "string", "Vocabulary name"),
            ("language_code", "string", "Language code"),
            ("phrases", "list(string)", "Vocabulary phrases"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_transcribe_vocabulary.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "vocabulary_name", f"{ref}.vocabulary_name", "Vocabulary name"
                ),
            ]
        )
