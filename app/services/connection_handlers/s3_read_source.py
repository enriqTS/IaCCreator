"""Managed input locations with consumer-owned external-role read policies."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.storage import S3LocationConfig
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_references import managed_key


class S3ReadSourceHandler(BaseConnectionHandler):
    def __init__(
        self, role_field: str, location_field: str, versioned: bool = False
    ) -> None:
        super().__init__()
        self.role_field = role_field
        self.location_field = location_field
        self.versioned = versioned

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Upload the required source files before creating the consumer. The configured external role must already trust the service and retain its other runtime/output permissions. External KMS keys and cross-account policies remain owner-managed.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        locations = {
            (
                item.target_name,
                S3LocationConfig.model_validate(item.connection_config).prefix,
            )
            for item in project.connections
            if item.source_name == connection.source_name
            and item.connection_type == connection.connection_type
        }
        if len(locations) != 1:
            self._reject(connection, "A service supports one managed S3 input location")
        bucket, prefix = next(iter(locations))
        source = self._find_instance(connection.source_name, project)
        if not getattr(source.config, self.role_field):
            self._reject(
                connection, "S3 input access requires an external service role ARN"
            )
        source.config._reads_s3_source = True
        setattr(source.config, self.location_field, "managed-by-connection")
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source.name,
                    name="source_data_bucket_arn",
                    value=f"module.{bucket}.bucket_arn",
                    description="Bucket containing service input",
                )
            ]
        )
        if self.versioned:
            result.inputs.append(
                ModuleInput(
                    module=bucket,
                    name="versioning_enabled",
                    value='"Enabled"',
                    description="MWAA requires a versioned source bucket",
                )
            )
            result.outputs.append(
                ModuleOutput(
                    module=bucket,
                    name="workflow_bucket_arn",
                    value=f"aws_s3_bucket.{bucket}.arn",
                    description="Workflow bucket after versioning",
                    depends_on=[f"aws_s3_bucket_versioning.{bucket}_versioning"],
                )
            )
            location = f"module.{bucket}.workflow_bucket_arn"
        else:
            location = f'format("s3://%s/%s", module.{bucket}.bucket_name, {self._renderer.render_expression(prefix)})'
        result.inputs.append(
            ModuleInput(
                module=source.name,
                name=self.location_field,
                value=location,
                description="Managed S3 source location",
            )
        )
        object_suffix = "*" if self.versioned else prefix + "*"
        statements = [
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
                "Resource": Expr("var.source_data_bucket_arn"),
            },
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:GetObjectVersion"],
                "Resource": Expr(
                    f'format("%s/%s", var.source_data_bucket_arn, {self._renderer.render_expression(object_suffix)})'
                ),
            },
        ]
        key = managed_key(bucket, project)
        if key:
            result.inputs.append(
                ModuleInput(
                    module=source.name,
                    name="source_data_key_arn",
                    value=f"module.{key}.key_arn",
                    description="Key decrypting source objects",
                )
            )
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": "kms:Decrypt",
                    "Resource": Expr("var.source_data_key_arn"),
                }
            )
        result.resources.append(
            self._resource(
                source.name,
                "source_data_policy.tf",
                self._renderer.render_resource(
                    "aws_iam_role_policy",
                    "source_data",
                    {
                        "name": f"{source.name}-source-data",
                        "role": Expr(
                            f'element(reverse(split("/", var.{self.role_field})), 0)'
                        ),
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
            [{"loc": ("source",), "msg": message}],
        )
