"""Render private ACM certificate references and native key/Region guards."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.private_certificate import PrivateCertificateBinding


def private_certificate_attributes(
    binding: PrivateCertificateBinding, renderer: HCLRenderer
) -> dict[str, object]:
    key = (
        Expr(
            'startswith(var.private_ca_key_algorithm, "RSA_") ? "RSA_2048" : var.private_ca_key_algorithm'
        )
        if binding.key_algorithm == "AUTO"
        else binding.key_algorithm
    )
    key_expression = renderer.render_expression(key)
    return {
        "certificate_authority_arn": Expr("var.private_ca_arn"),
        "key_algorithm": key,
        "lifecycle": {
            "create_before_destroy": True,
            "precondition": [
                {
                    "condition": Expr(
                        'split(":", var.private_ca_arn)[3] == data.aws_region.private_certificate.name'
                    ),
                    "error_message": "The private CA and ACM certificate must use the same AWS Region.",
                },
                {
                    "condition": Expr(
                        f'startswith(({key_expression}), "RSA_") == startswith(var.private_ca_key_algorithm, "RSA_")'
                    ),
                    "error_message": "The ACM certificate key must match the CA's RSA or ECDSA family.",
                },
            ],
        },
    }
