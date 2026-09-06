"""CloudTrail encryption with a key-owned policy and cycle-free trail identity."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class KmsCloudTrailHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        keys = {
            item.source_name
            for item in project.connections
            if item.target_name == connection.target_name
            and item.source_service == ServiceType.KMS
            and item.connection_type == "encrypts"
        }
        if len(keys) > 1:
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                "encrypts",
                [{"loc": ("source",), "msg": "A trail can use only one KMS key"}],
            )
        peers = [
            item
            for item in project.connections
            if item.source_name == connection.source_name
            and item.target_service == ServiceType.CLOUDTRAIL
            and item.connection_type == "encrypts"
        ]
        first_target = next(
            item for item in peers if item.target_name == connection.target_name
        )
        if connection is not first_target:
            return ConnectionContribution()
        target = self._find_instance(connection.target_name, project)
        if target is not None:
            target.config.kms_key_id = "managed-by-connection"
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name="kms_key_id",
                    value=f"module.{connection.source_name}.cloudtrail_key_arn",
                    description="KMS key with CloudTrail permissions installed",
                )
            ],
            outputs=[
                self._output(
                    connection.target_name,
                    "encryption_trail_arn",
                    '"arn:${data.aws_partition.encryption.partition}:cloudtrail:${data.aws_region.encryption.region}:${data.aws_caller_identity.encryption.account_id}:trail/${var.trail_name}"',
                    "Trail identity independent of trail creation",
                )
            ],
            resources=[
                self._resource(
                    connection.target_name,
                    "encryption_identity.tf",
                    'data "aws_partition" "encryption" {}\n'
                    'data "aws_region" "encryption" {}\n'
                    'data "aws_caller_identity" "encryption" {}\n',
                )
            ],
        )
        if connection is not peers[0]:
            return result
        targets = sorted({item.target_name for item in peers})
        result.inputs.append(
            ModuleInput(
                module=connection.source_name,
                name="cloudtrail_arns",
                type="list(string)",
                value="["
                + ", ".join(f"module.{name}.encryption_trail_arn" for name in targets)
                + "]",
                description="Trails authorized to encrypt with this key",
            )
        )
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "EnableAccountPermissions",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": Expr(
                            '"arn:${data.aws_partition.cloudtrail_policy.partition}:iam::${data.aws_caller_identity.cloudtrail_policy.account_id}:root"'
                        )
                    },
                    "Action": "kms:*",
                    "Resource": "*",
                },
                {
                    "Sid": "CloudTrailEncryption",
                    "Effect": "Allow",
                    "Principal": {"Service": "cloudtrail.amazonaws.com"},
                    "Action": "kms:GenerateDataKey*",
                    "Resource": "*",
                    "Condition": {
                        "StringEquals": {
                            "aws:SourceArn": Expr("var.cloudtrail_arns"),
                            "kms:EncryptionContext:aws:cloudtrail:arn": Expr(
                                "var.cloudtrail_arns"
                            ),
                        }
                    },
                },
                {
                    "Sid": "CloudTrailDescribe",
                    "Effect": "Allow",
                    "Principal": {"Service": "cloudtrail.amazonaws.com"},
                    "Action": "kms:DescribeKey",
                    "Resource": "*",
                    "Condition": {
                        "StringEquals": {"aws:SourceArn": Expr("var.cloudtrail_arns")}
                    },
                },
            ],
        }
        content = (
            'data "aws_partition" "cloudtrail_policy" {}\n'
            'data "aws_caller_identity" "cloudtrail_policy" {}\n'
        ) + self._renderer.render_resource(
            "aws_kms_key_policy",
            "cloudtrail",
            {
                "key_id": Expr(f"aws_kms_key.{connection.source_name}.arn"),
                "policy": self._renderer.render_json_policy(policy),
            },
        )
        result.resources.append(
            self._resource(connection.source_name, "cloudtrail_policy.tf", content)
        )
        result.outputs.append(
            self._output(
                connection.source_name,
                "cloudtrail_key_arn",
                "aws_kms_key_policy.cloudtrail.key_id",
                "Key ARN available after the CloudTrail policy is installed",
            )
        )
        return result
