"""Wire issued ACM certificates into native Client VPN authentication inputs."""

from app.models.connection_configs.client_vpn_certificate import (
    ClientVpnCertificateConfig,
)
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.certificate_readiness import issued_certificate
from app.services.connection_handlers.client_vpn_certificate_bindings import (
    ROLE_FIELDS,
    resolve_client_vpn_certificates,
)
from app.services.connection_handlers.private_certificate_bindings import (
    resolve_private_certificate_binding,
)


class ClientVpnCertificateHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        bindings = resolve_client_vpn_certificates(connection.target_name, project)
        self._find_instance(
            connection.target_name, project
        ).config._managed_certificate_fields = tuple(bindings)
        request = ClientVpnCertificateConfig.model_validate(
            connection.connection_config
        )
        name = connection.source_name
        certificate = f"aws_acm_certificate.{name}"
        contribution = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name=field,
                    value=f"module.{name}.client_vpn_certificate_arn",
                    description="Issued ACM certificate reference",
                )
                for field in ROLE_FIELDS[request.certificate_role]
            ]
            + [
                ModuleInput(
                    module=connection.target_name,
                    name=f"{field}_key_algorithm",
                    value=f"module.{name}.client_vpn_certificate_key_algorithm",
                    description="Native ACM certificate key algorithm",
                )
                for field in ROLE_FIELDS[request.certificate_role]
            ],
            outputs=[
                self._output(
                    name,
                    "client_vpn_certificate_key_algorithm",
                    f"{certificate}.key_algorithm",
                    "Native ACM certificate key algorithm",
                )
            ],
        )
        ready, issuance = issued_certificate(name, project, self._renderer)
        contribution.merge(issuance)
        contribution.outputs.append(
            self._output(
                name,
                "client_vpn_certificate_arn",
                ready,
                "Issued certificate ready for Client VPN",
            )
        )
        return contribution

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        bindings = resolve_client_vpn_certificates(connection.target_name, project)
        endpoint = self._find_instance(connection.target_name, project)
        issues = [
            ConnectionIssue(
                severity="warning",
                message="Provision individual client certificates and private keys from the selected client CA, install the server CA root in client trust stores, and distribute VPN profiles separately. Subnet placement, authorization rules, routing, and revocation remain required for usable access.",
            )
        ]
        if resolve_private_certificate_binding(connection.source_name, project) is None:
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="Complete the public ACM certificate's DNS or email validation before the issuance waiter can create the VPN endpoint; this connection does not create validation records.",
                )
            )
        for field in ("server_certificate_arn", "root_certificate_chain_arn"):
            if field not in bindings and not getattr(endpoint.config, field):
                issues.append(
                    ConnectionIssue(
                        severity="warning",
                        message=f"Configure {field} or add a certificate connection for that role before applying.",
                    )
                )
        return issues
