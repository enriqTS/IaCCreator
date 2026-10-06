"""Native guards for stable ACM validation-record ownership."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.certificate_dns import dns_name


def certificate_dns_preconditions(
    domains: list[str], renderer: HCLRenderer
) -> list[dict]:
    names = renderer.render_expression(sorted({dns_name(name) for name in domains}))
    return [
        {
            "condition": Expr('var.validation_method == "DNS"'),
            "error_message": "Managed validation records require DNS certificate validation.",
        },
        {
            "condition": Expr(
                f'toset([for name in concat([var.domain_name], var.subject_alternative_names) : lower(trimprefix(name, "*."))]) == toset({names})'
            ),
            "error_message": "Regenerate the project after changing the certificate validation domains.",
        },
    ]


def zone_dns_preconditions(zone: str, domain: str) -> list[dict]:
    native_zone = f"aws_route53_zone.{zone}"
    return [
        {
            "condition": Expr(f"length({native_zone}.vpc) == 0"),
            "error_message": "ACM DNS validation requires a public hosted zone.",
        },
        {
            "condition": Expr(
                f'lower(trimsuffix({native_zone}.name, ".")) == "{domain}"'
            ),
            "error_message": "Regenerate the project after changing the validation hosted-zone name.",
        },
    ]
