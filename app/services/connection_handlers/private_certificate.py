"""Managed root CA issuance and renewal support for ACM private certificates."""

from app.generators.private_ca_activation import render_acm_issuer
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.private_certificate_bindings import (
    resolve_private_certificate_binding,
)


class PrivateCertificateHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        binding = resolve_private_certificate_binding(connection.target_name, project)
        self._find_instance(
            connection.target_name, project
        ).config._private_ca = binding
        name = binding.authority_name
        authority = f"aws_acmpca_certificate_authority.{name}"
        activation = (
            f"aws_acmpca_certificate_authority_certificate.{name}_acm_activation"
        )
        permission = f"aws_acmpca_permission.{name}_acm_renewal"
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name="private_ca_arn",
                    value=f"module.{name}.acm_issuer_arn",
                    description="Activated private CA with ACM renewal permissions",
                ),
                ModuleInput(
                    module=connection.target_name,
                    name="private_ca_key_algorithm",
                    value=f"module.{name}.acm_issuer_key_algorithm",
                    description="Native issuing CA key algorithm",
                ),
            ],
            outputs=[
                ModuleOutput(
                    module=name,
                    name="acm_issuer_arn",
                    value=f"{authority}.arn",
                    description="Private CA ready for ACM certificate issuance",
                    depends_on=[activation, permission],
                ),
                ModuleOutput(
                    module=name,
                    name="acm_issuer_key_algorithm",
                    value=f"{authority}.certificate_authority_configuration[0].key_algorithm",
                    description="Issuing CA key algorithm",
                ),
                ModuleOutput(
                    module=name,
                    name="root_certificate",
                    value=f"aws_acmpca_certificate.{name}_acm_root.certificate",
                    description="Root CA PEM certificate for client trust stores",
                    depends_on=[activation],
                ),
            ],
            resources=[
                self._resource(
                    name, "acm_issuance.tf", render_acm_issuer(name, self._renderer)
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_private_certificate_binding(connection.target_name, project)
        return [
            ConnectionIssue(
                severity="warning",
                message="This connection activates a self-signed root CA with a ten-year certificate. Install its root certificate in client trust stores. ACM renewal requires the CA to remain active and the certificate to be associated with an AWS service or exported; CA expiry and revocation configuration remain operational responsibilities.",
            )
        ]
