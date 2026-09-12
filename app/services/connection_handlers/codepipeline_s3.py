"""Pipeline-owned artifact store references and external-role permissions."""

import json

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_references import managed_key


class CodePipelineS3Handler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The external pipeline role must trust CodePipeline and have permissions for the configured actions. This connection grants only artifact-bucket and managed artifact-key access. Cross-region action artifact stores are not modeled.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        source = self._find_instance(connection.source_name, project)
        targets = {
            item.target_name
            for item in project.connections
            if item.source_name == source.name
            and item.connection_type == "stores_artifacts"
        }
        stages = json.loads(source.config.stages_json)
        if len(targets) != 1 or not source.config.role_arn or len(stages) < 2:
            self._reject(
                connection,
                "An artifact store requires one bucket, an external pipeline role, and at least two configured stages",
            )
        if any(action.get("region") for stage in stages for action in stage["actions"]):
            self._reject(
                connection,
                "Action region overrides require cross-region artifact stores, which are not supported",
            )
        source.config.artifact_bucket_name = "managed-by-connection"
        source.config._managed_artifacts = True
        bucket = connection.target_name
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source.name,
                    name="artifact_bucket_name",
                    value=f"module.{bucket}.bucket_name",
                    description="Managed artifact bucket",
                ),
                ModuleInput(
                    module=source.name,
                    name="artifact_bucket_arn",
                    value=f"module.{bucket}.bucket_arn",
                    description="Artifact policy scope",
                ),
            ]
        )
        statements = [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetBucketVersioning",
                    "s3:GetBucketAcl",
                    "s3:GetBucketLocation",
                    "s3:ListBucket",
                ],
                "Resource": Expr("var.artifact_bucket_arn"),
            },
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject"],
                "Resource": Expr('"${var.artifact_bucket_arn}/*"'),
            },
        ]
        key = managed_key(bucket, project)
        if key:
            source.config.artifact_kms_key_arn = "managed-by-connection"
            result.inputs.append(
                ModuleInput(
                    module=source.name,
                    name="artifact_kms_key_arn",
                    value=f"module.{key}.key_arn",
                    description="Artifact encryption key",
                )
            )
        if source.config.artifact_kms_key_arn:
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": [
                        "kms:Encrypt",
                        "kms:Decrypt",
                        "kms:ReEncrypt*",
                        "kms:GenerateDataKey*",
                        "kms:DescribeKey",
                    ],
                    "Resource": Expr("var.artifact_kms_key_arn"),
                }
            )
        result.resources.append(
            self._resource(
                source.name,
                "artifact_policy.tf",
                self._renderer.render_resource(
                    "aws_iam_role_policy",
                    "artifacts",
                    {
                        "name": f"{source.name}-artifacts",
                        "role": Expr('element(reverse(split("/", var.role_arn)), 0)'),
                        "policy": self._renderer.render_json_policy(
                            {"Version": "2012-10-17", "Statement": statements}
                        ),
                    },
                ),
            )
        )
        return result

    @staticmethod
    def _reject(connection: ConnectionIR, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": ("artifact_store",), "msg": message}],
        )
