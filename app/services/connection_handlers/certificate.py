"""Certificate references for load balancers and CloudFront."""

from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class CertificateLoadBalancerHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        certificate = safe_identifier(connection.source_name)
        return ConnectionContribution(
            inputs=[
                self._input(
                    connection.target_name,
                    connection.source_name,
                    "certificate_arn",
                    f"module.{connection.source_name}.certificate_arn",
                    f"Certificate supplied by {certificate}",
                )
            ]
        )


class CertificateCloudFrontHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = self._find_instance(connection.target_name, project)
        if target is not None:
            target.config.certificate_arn = "managed-by-connection"
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name="certificate_arn",
                    value=f"module.{connection.source_name}.certificate_arn",
                    description="ACM viewer certificate ARN",
                )
            ]
        )
