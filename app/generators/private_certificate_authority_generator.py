from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.private_certificate_authority_config import (
    PrivateCertificateAuthorityConfig,
)
from app.models.ir_models import ResourceInstanceIR


class PrivateCertificateAuthorityGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, PrivateCertificateAuthorityConfig)
        return self._r.render_resource(
            "aws_acmpca_certificate_authority",
            instance.name,
            {
                "type": "ROOT",
                "key_algorithm": Expr("var.key_algorithm"),
                "signing_algorithm": Expr("var.signing_algorithm"),
                "usage_mode": Expr("var.usage_mode"),
                "subject": {
                    "common_name": Expr("var.common_name"),
                    "organization": Expr("var.organization"),
                },
                "permanent_deletion_time_in_days": Expr(
                    "var.permanent_deletion_time_in_days"
                ),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, PrivateCertificateAuthorityConfig)
        fields = [
            ("common_name", "string", "CA common name"),
            ("organization", "string", "CA organization"),
            ("key_algorithm", "string", "Key algorithm"),
            ("signing_algorithm", "string", "Signing algorithm"),
            ("usage_mode", "string", "Usage mode"),
            ("permanent_deletion_time_in_days", "number", "Restoration period"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_acmpca_certificate_authority.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "certificate_authority_id", f"{ref}.id", "Certificate authority ID"
                ),
                self._r.render_output(
                    "certificate_authority_arn",
                    f"{ref}.arn",
                    "Certificate authority ARN",
                ),
            ]
        )
