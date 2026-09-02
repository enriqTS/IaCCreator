"""KMS encryption references for services with native key inputs."""

from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class KmsEncryptionHandler(BaseConnectionHandler):
    def __init__(self, input_name: str, output_name: str = "key_arn") -> None:
        super().__init__()
        self._input_name = input_name
        self._output_name = output_name

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = self._find_instance(connection.target_name, project)
        if target is not None:
            setattr(target.config, self._input_name, "managed-by-connection")
            if connection.target_service == ServiceType.S3:
                target.config.sse_algorithm = "aws:kms"
            elif connection.target_service == ServiceType.DYNAMODB:
                target.config.server_side_encryption_enabled = True
            elif connection.target_service == ServiceType.EBS:
                target.config.encrypted = True
        contribution = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name=self._input_name,
                    value=f"module.{connection.source_name}.{self._output_name}",
                    description="KMS key supplied by a managed connection",
                )
            ]
        )
        if connection.target_service == ServiceType.LAMBDA:
            contribution.iam.append(
                self._grant(
                    connection.target_name,
                    IAMStatement(
                        actions=["kms:Decrypt", "kms:DescribeKey"],
                        resources=[f"${{var.{self._input_name}}}"],
                    ),
                )
            )
        return contribution
