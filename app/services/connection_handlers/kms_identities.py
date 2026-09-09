"""Pre-creation service identities keep key policies independent of encrypted resources."""

from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ModuleOutput,
    ModuleResource,
    ResourceInstanceIR,
)

_IDENTITY_FIELDS = {
    ServiceType.CLOUDTRAIL: (
        "encryption_trail_arn",
        "cloudtrail",
        "trail/${var.trail_name}",
    ),
    ServiceType.CLOUDWATCH: (
        "encryption_log_group_arn",
        "logs",
        "log-group:${var.log_group_name}",
    ),
    ServiceType.SNS: ("encryption_topic_arn", "sns", "${var.topic_name}"),
}


def identity(instance: ResourceInstanceIR) -> tuple[str, ConnectionContribution]:
    output, service, suffix = _IDENTITY_FIELDS[instance.service_type]
    expression = f'"arn:${{data.aws_partition.kms_identity.partition}}:{service}:${{data.aws_region.kms_identity.region}}:${{data.aws_caller_identity.kms_identity.account_id}}:{suffix}"'
    contribution = ConnectionContribution(
        outputs=[
            ModuleOutput(
                module=instance.name,
                name=output,
                value=expression,
                description="Service identity independent of resource creation",
            )
        ],
        resources=[
            ModuleResource(
                module=instance.name,
                filename="encryption_identity.tf",
                content='data "aws_partition" "kms_identity" {}\ndata "aws_region" "kms_identity" {}\ndata "aws_caller_identity" "kms_identity" {}\n',
            )
        ],
    )
    return f"module.{instance.name}.{output}", contribution
