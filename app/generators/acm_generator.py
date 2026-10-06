"""Terraform generator for ACM certificates."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.private_certificate import private_certificate_attributes
from app.models.input_models.acm_config import AcmConfig
from app.models.ir_models import ResourceInstanceIR


class AcmGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, AcmConfig)
        attrs = {
            "domain_name": Expr("var.domain_name"),
            "subject_alternative_names": Expr("var.subject_alternative_names"),
        }
        prefix = ""
        if config._private_ca is None:
            attrs["validation_method"] = Expr("var.validation_method")
            attrs["lifecycle"] = {"create_before_destroy": True}
        else:
            attrs.update(private_certificate_attributes(config._private_ca, self._r))
            prefix = 'data "aws_region" "private_certificate" {}\n\n'
        return prefix + self._r.render_resource(
            "aws_acm_certificate",
            instance.name,
            attrs,
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, AcmConfig)
        parts = [
            self._r.render_variable(
                "domain_name", "string", "Primary certificate domain"
            ),
            self._r.render_variable(
                "subject_alternative_names",
                "list(string)",
                "Additional certificate domains",
            ),
        ]
        if config._private_ca is None:
            parts.append(
                self._r.render_variable(
                    "validation_method", "string", "Certificate validation method"
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, AcmConfig)
        ref = f"aws_acm_certificate.{instance.name}"
        parts = [
            self._r.render_output("certificate_arn", f"{ref}.arn", "Certificate ARN")
        ]
        if config._private_ca is None:
            parts.append(
                self._r.render_output(
                    "domain_validation_options",
                    f"{ref}.domain_validation_options",
                    "DNS validation records",
                )
            )
        return "\n".join(parts)
