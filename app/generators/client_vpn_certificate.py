"""Native Region and leaf-key guards for managed VPN certificates."""

from app.generators.hcl_renderer import Expr


def certificate_preconditions(fields: tuple[str, ...]) -> list[dict[str, object]]:
    return [
        guard
        for field in fields
        for guard in (
            {
                "condition": Expr(
                    f'split(":", var.{field})[3] == data.aws_region.client_vpn_certificate.name'
                ),
                "error_message": "Client VPN and its ACM certificates must use the same AWS Region.",
            },
            {
                "condition": Expr(
                    f'contains(["RSA_1024", "RSA_2048"], var.{field}_key_algorithm)'
                ),
                "error_message": "Client VPN certificates require RSA 1024 or RSA 2048 keys.",
            },
        )
    ]
