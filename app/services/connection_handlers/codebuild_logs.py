"""Build modules own logging permissions while CloudWatch owns log storage."""

from app.generators.codebuild_logs import render_build_log_resources
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.codebuild_logs_bindings import resolve_build_logs
from app.services.connection_handlers.kms_external_policy import (
    external_service_key_issues,
)


class CodeBuildLogsHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        request = resolve_build_logs(connection, project)
        source = connection.source_name
        target = connection.target_name
        self._find_instance(source, project).config._cloudwatch_logs = True
        ref = f"aws_cloudwatch_log_group.{target}"
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source,
                    name="build_logs",
                    type="object({ arn = string, name = string, log_group_class = string, kms_key_arn = string, stream_prefix = string })",
                    value=self._renderer.render_expression(
                        {
                            "arn": Expr(f"module.{target}.log_group_arn"),
                            "name": Expr(f"module.{target}.log_group_name"),
                            "log_group_class": Expr(f"module.{target}.log_group_class"),
                            "kms_key_arn": Expr(
                                f"module.{target}.log_group_kms_key_arn"
                            ),
                            "stream_prefix": request.stream_prefix,
                        }
                    ),
                    description="Native build-log destination and stream prefix",
                )
            ],
            outputs=[
                *[
                    self._output(
                        target, name, value, "Native CloudWatch log-group metadata"
                    )
                    for name, value in {
                        "log_group_name": f"{ref}.name",
                        "log_group_class": f"{ref}.log_group_class",
                        "log_group_kms_key_arn": f'{ref}.kms_key_id == null ? "" : {ref}.kms_key_id',
                    }.items()
                ],
                self._output(
                    source,
                    "build_log_destination",
                    "var.build_logs",
                    "Native build-log destination and stream prefix",
                ),
            ],
            resources=[
                self._resource(
                    source, "build_logs.tf", render_build_log_resources(self._renderer)
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_build_logs(connection, project)
        return [
            *external_service_key_issues(connection, project),
            ConnectionIssue(
                severity="warning",
                message="Build output is sent to the connected log group under the selected stream prefix. The build-owned inline policy grants group creation for that exact group and stream creation/writes for names beginning with the prefix. The existing external service role must trust codebuild.amazonaws.com; the deployment identity must read it with iam:GetRole, manage inline policies, and pass it to CodeBuild. Terraform checks the full role ARN before policy attachment. Shared roles retain the union of all attached permissions. Retention, tags, class, and encryption belong to CloudWatch. Encrypted logs add key-scoped caller permissions through regional Logs, with cryptographic actions constrained to the group encryption context; external key policies must authorize both Logs and the service role. Configure build commands, source access, network reachability, and any artifact permissions separately. Build output can expose secrets printed by commands and incurs ingestion/storage costs. The connection configures project defaults; externally authorized StartBuild logging or service-role overrides are outside its control.",
            ),
        ]
