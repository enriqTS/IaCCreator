from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.comprehend_config import ComprehendConfig
from app.models.ir_models import ResourceInstanceIR


class ComprehendGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, ComprehendConfig)
        return self._r.render_resource(
            "aws_comprehend_document_classifier",
            instance.name,
            {
                "name": Expr("var.classifier_name"),
                "data_access_role_arn": Expr("var.data_access_role_arn"),
                "language_code": Expr("var.language_code"),
                "input_data_config": {"s3_uri": Expr("var.training_data_s3_uri")},
                "output_data_config": {"s3_uri": Expr("var.output_data_s3_uri")},
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, ComprehendConfig)
        fields = [
            ("classifier_name", "string", "Document classifier name"),
            ("data_access_role_arn", "string", "Training data IAM role ARN"),
            ("language_code", "string", "Training language code"),
            ("training_data_s3_uri", "string", "Training data S3 URI"),
            ("output_data_s3_uri", "string", "Output data S3 URI"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_comprehend_document_classifier.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("classifier_arn", f"{ref}.arn", "Classifier ARN"),
                self._r.render_output(
                    "classifier_name", f"{ref}.name", "Classifier name"
                ),
            ]
        )
