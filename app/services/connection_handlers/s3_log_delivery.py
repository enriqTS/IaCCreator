"""Aggregate audit-service delivery permissions in one bucket-owned policy."""

from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.s3_bucket_policy import S3BucketPolicy

DELIVERY_SERVICES = {ServiceType.CLOUDTRAIL, ServiceType.AWS_CONFIG}


class S3LogDeliveryHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Delivery uses a bucket-owned service policy. AWS Config still requires its configured recorder role and recording permissions. KMS-encrypted delivery requires appropriate service/role key permissions; configure those separately.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        return S3BucketPolicy().build(connection.target_name, project)
