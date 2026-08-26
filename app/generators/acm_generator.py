"""Terraform generator for ACM certificates."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.acm_config import AcmConfig
from app.models.ir_models import ResourceInstanceIR


class AcmGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, AcmConfig)
        return self._r.render_resource(
            "aws_acm_certificate",
            instance.name,
            {
                "domain_name": Expr("var.domain_name"),
                "subject_alternative_names": Expr("var.subject_alternative_names"),
                "validation_method": Expr("var.validation_method"),
                "lifecycle": {"create_before_destroy": True},
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, AcmConfig)
        return "\n".join(
            [
                self._r.render_variable(
                    "domain_name", "string", "Primary certificate domain"
                ),
                self._r.render_variable(
                    "subject_alternative_names",
                    "list(string)",
                    "Additional certificate domains",
                ),
                self._r.render_variable(
                    "validation_method", "string", "Certificate validation method"
                ),
            ]
        )

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_acm_certificate.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "certificate_arn", f"{ref}.arn", "Certificate ARN"
                ),
                self._r.render_output(
                    "domain_validation_options",
                    f"{ref}.domain_validation_options",
                    "DNS validation records",
                ),
            ]
        )
