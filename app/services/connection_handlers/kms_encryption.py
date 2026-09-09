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
from app.services.connection_handlers.kms_references import managed_key
from app.services.connection_handlers.kms_service_policy import (
    KmsServicePolicy,
    needs_service_policy,
)


class KmsEncryptionHandler(BaseConnectionHandler):
    def __init__(self, input_name: str, output_name: str = "key_arn") -> None:
        super().__init__()
        self._input_name = input_name
        self._output_name = output_name

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        managed_key(connection.target_name, project)
        policy_required = needs_service_policy(connection.source_name, project)
        output = "service_key_arn" if policy_required else self._output_name
        if connection.target_service == ServiceType.CLOUDTRAIL:
            output = "cloudtrail_key_arn"
        target = self._find_instance(connection.target_name, project)
        if target is not None:
            setattr(target.config, self._input_name, "managed-by-connection")
            if connection.target_service == ServiceType.S3:
                if target.config.sse_algorithm != "aws:kms:dsse":
                    target.config.sse_algorithm = "aws:kms"
            elif connection.target_service == ServiceType.DYNAMODB:
                target.config.server_side_encryption_enabled = True
            elif connection.target_service in {ServiceType.EBS, ServiceType.EFS}:
                target.config.encrypted = True
        contribution = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name=self._input_name,
                    value=f"module.{connection.source_name}.{output}",
                    description="KMS key supplied by a managed connection",
                )
            ]
        )
        peers = [
            item
            for item in project.connections
            if item.source_name == connection.source_name
            and item.source_service == ServiceType.KMS
            and item.connection_type == "encrypts"
        ]
        if policy_required and connection is peers[0]:
            contribution.merge(
                KmsServicePolicy().build(connection.source_name, project)
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
