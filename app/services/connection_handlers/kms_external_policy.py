"""External key policies remain owned outside the generated project."""

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_references import KMS_INPUTS, managed_key


def require_custom_delivery_key(connection: ConnectionIR, project: ProjectIR) -> None:
    target = BaseConnectionHandler._find_instance(connection.target_name, project)
    if (
        target is None
        or target.service_type not in {ServiceType.SQS, ServiceType.SNS}
        or managed_key(target.name, project)
    ):
        return
    key = getattr(target.config, "kms_master_key_id", None) or ""
    if key.startswith("alias/aws/") or ":alias/aws/" in key:
        raise InvalidConnectionConfigError(
            connection.source_name,
            target.name,
            connection.connection_type,
            [
                {
                    "loc": ("kms_master_key_id",),
                    "msg": "AWS service delivery to an encrypted destination requires a customer-managed KMS key",
                }
            ],
        )


def external_service_key_issues(
    connection: ConnectionIR, project: ProjectIR
) -> list[ConnectionIssue]:
    target = BaseConnectionHandler._find_instance(connection.target_name, project)
    field = KMS_INPUTS.get(connection.target_service)
    if (
        target is None
        or field is None
        or managed_key(target.name, project)
        or not getattr(target.config, field, None)
    ):
        return []
    return [
        ConnectionIssue(
            severity="warning",
            message="The external KMS key owner must authorize the delivering AWS service in its key policy; AWS-managed keys cannot be customized for service delivery.",
        )
    ]
