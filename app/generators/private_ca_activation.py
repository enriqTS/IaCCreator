"""Render root signing, activation, and ACM renewal permissions in the CA module."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.private_certificate import (
    ECDSA_CA_KEYS,
    ECDSA_SIGNATURES,
    RSA_CA_KEYS,
    RSA_SIGNATURES,
)


def render_acm_issuer(name: str, renderer: HCLRenderer) -> str:
    authority = f"aws_acmpca_certificate_authority.{name}"
    rsa_keys = renderer.render_expression(list(RSA_CA_KEYS))
    rsa_signatures = renderer.render_expression(list(RSA_SIGNATURES))
    ec_keys = renderer.render_expression(list(ECDSA_CA_KEYS))
    ec_signatures = renderer.render_expression(list(ECDSA_SIGNATURES))
    root = renderer.render_resource(
        "aws_acmpca_certificate",
        f"{name}_acm_root",
        {
            "certificate_authority_arn": Expr(f"{authority}.arn"),
            "certificate_signing_request": Expr(
                f"{authority}.certificate_signing_request"
            ),
            "signing_algorithm": Expr("var.signing_algorithm"),
            "template_arn": Expr(
                f'format("arn:%s:acm-pca:::template/RootCACertificate/V1", split(":", {authority}.arn)[1])'
            ),
            "validity": {"type": "YEARS", "value": 10},
            "lifecycle": {
                "precondition": [
                    {
                        "condition": Expr('var.usage_mode == "GENERAL_PURPOSE"'),
                        "error_message": "ACM private certificates require a GENERAL_PURPOSE issuing CA.",
                    },
                    {
                        "condition": Expr(
                            f"(contains({rsa_keys}, var.key_algorithm) && contains({rsa_signatures}, var.signing_algorithm)) || (contains({ec_keys}, var.key_algorithm) && contains({ec_signatures}, var.signing_algorithm))"
                        ),
                        "error_message": "Use a supported RSA or ECDSA CA key with a matching signing algorithm.",
                    },
                ]
            },
        },
    )
    activation = renderer.render_resource(
        "aws_acmpca_certificate_authority_certificate",
        f"{name}_acm_activation",
        {
            "certificate_authority_arn": Expr(f"{authority}.arn"),
            "certificate": Expr(f"aws_acmpca_certificate.{name}_acm_root.certificate"),
        },
    )
    permission = renderer.render_resource(
        "aws_acmpca_permission",
        f"{name}_acm_renewal",
        {
            "certificate_authority_arn": Expr(f"{authority}.arn"),
            "principal": "acm.amazonaws.com",
            "source_account": Expr(f'split(":", {authority}.arn)[4]'),
            "actions": ["IssueCertificate", "GetCertificate", "ListPermissions"],
            "depends_on": [
                Expr(
                    f"aws_acmpca_certificate_authority_certificate.{name}_acm_activation"
                )
            ],
        },
    )
    return "\n".join([root, activation, permission])
