"""Derive resource-scoped KMS grants from concrete data-plane IAM actions."""

from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_references import KMS_INPUTS, managed_key


def key_actions(service: ServiceType, actions: list[str]) -> list[str]:
    required: set[str] = set()
    if service == ServiceType.S3:
        if "s3:GetObject" in actions:
            required.add("kms:Decrypt")
        if "s3:PutObject" in actions:
            required.update(["kms:Decrypt", "kms:GenerateDataKey"])
    elif service == ServiceType.SQS:
        if "sqs:ReceiveMessage" in actions:
            required.add("kms:Decrypt")
        if "sqs:SendMessage" in actions:
            required.update(["kms:Decrypt", "kms:GenerateDataKey"])
    elif service == ServiceType.SNS and "sns:Publish" in actions:
        required.update(["kms:Decrypt", "kms:GenerateDataKey*"])
    elif service == ServiceType.CLOUDWATCH and "logs:PutLogEvents" in actions:
        required.update(
            [
                "kms:Encrypt",
                "kms:Decrypt",
                "kms:ReEncrypt*",
                "kms:GenerateDataKey*",
                "kms:DescribeKey",
            ]
        )
    return sorted(required)


class KmsConsumerGrants(BaseConnectionHandler):
    def augment(
        self, result: ConnectionContribution, target_name: str, project: ProjectIR
    ) -> ConnectionContribution:
        target = self._find_instance(target_name, project)
        if target is None or target.service_type not in KMS_INPUTS:
            return result
        key = managed_key(target_name, project)
        field = KMS_INPUTS[target.service_type]
        external = getattr(target.config, field, None)
        if not key and not external:
            return result
        if (
            not key
            and target.service_type == ServiceType.S3
            and target.config.sse_algorithm not in ("aws:kms", "aws:kms:dsse")
        ):
            return result
        for grant in list(result.iam):
            actions = key_actions(target.service_type, grant.statement.actions)
            if not actions:
                continue
            variable = f"kms_access_{target_name}_arn"
            if key:
                result.inputs.append(
                    ModuleInput(
                        module=grant.role_owner,
                        name=variable,
                        value=f"module.{key}.key_arn",
                        description="Key used by the connected encrypted resource",
                    )
                )
                arn = "${var." + variable + "}"
            else:
                output = "kms_access_key_id"
                result.outputs.append(self._output(target_name, output, f"var.{field}"))
                result.inputs.append(
                    ModuleInput(
                        module=grant.role_owner,
                        name=variable,
                        value=f"module.{target_name}.{output}",
                        description="External encryption key identifier",
                    )
                )
                result.resources.append(
                    self._resource(
                        grant.role_owner,
                        f"{variable}.tf",
                        f'data "aws_kms_key" "{variable}" {{\n  key_id = var.{variable}\n}}\n',
                    )
                )
                arn = "${data.aws_kms_key." + variable + ".arn}"
            result.iam.append(
                self._grant(
                    grant.role_owner, IAMStatement(actions=actions, resources=[arn])
                )
            )
        return result
