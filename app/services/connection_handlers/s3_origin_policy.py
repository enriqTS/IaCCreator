"""Distribution-scoped read permissions for private S3 origins."""

from app.generators.hcl_renderer import Expr
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ModuleInput, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler


class S3OriginPolicy(BaseConnectionHandler):
    def build(
        self, bucket: str, project: ProjectIR
    ) -> tuple[list[dict], ConnectionContribution]:
        sources = sorted(
            {
                item.source_name
                for item in project.connections
                if item.target_name == bucket
                and item.source_service == ServiceType.CLOUDFRONT
                and item.connection_type == "origin"
            }
        )
        result = ConnectionContribution()
        statements = []
        for source in sources:
            variable = f"origin_{source}_arn"
            result.inputs.append(
                ModuleInput(
                    module=bucket,
                    name=variable,
                    value=f"module.{source}.distribution_arn",
                    description="Distribution allowed to read origin objects",
                )
            )
            statements.append(
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "cloudfront.amazonaws.com"},
                    "Action": "s3:GetObject",
                    "Resource": Expr(f'"${{aws_s3_bucket.{bucket}.arn}}/*"'),
                    "Condition": {
                        "StringEquals": {"aws:SourceArn": Expr(f"var.{variable}")}
                    },
                }
            )
        return statements, result
