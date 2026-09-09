"""Native key fields and unambiguous managed-key lookup."""

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ServiceType
from app.models.ir_models import ProjectIR

KMS_INPUTS = {
    ServiceType.S3: "sse_kms_key_id",
    ServiceType.DYNAMODB: "server_side_encryption_kms_key_arn",
    ServiceType.SNS: "kms_master_key_id",
    ServiceType.SQS: "kms_master_key_id",
    ServiceType.CLOUDWATCH: "kms_key_id",
    ServiceType.EBS: "kms_key_id",
    ServiceType.EFS: "kms_key_id",
    ServiceType.BACKUP: "kms_key_arn",
    ServiceType.SECRETS_MANAGER: "kms_key_id",
    ServiceType.DATAZONE: "kms_key_identifier",
    ServiceType.CODEARTIFACT: "kms_key",
    ServiceType.LAMBDA: "kms_key_arn",
    ServiceType.CLOUDTRAIL: "kms_key_id",
}


def managed_key(target: str, project: ProjectIR) -> str | None:
    keys = sorted(
        {
            item.source_name
            for item in project.connections
            if item.source_service == ServiceType.KMS
            and item.target_name == target
            and item.connection_type == "encrypts"
        }
    )
    if len(keys) > 1:
        raise InvalidConnectionConfigError(
            keys[0],
            target,
            "encrypts",
            [{"loc": ("source",), "msg": "A resource can use only one KMS key"}],
        )
    return keys[0] if keys else None
