"""Execution logging owns its external-role policy while CloudWatch owns storage."""

from app.generators.hcl_renderer import Expr
from app.generators.step_functions_logs import (
    render_workflow_logs,
    workflow_log_destination,
)
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_external_policy import (
    external_service_key_issues,
)
from app.services.connection_handlers.step_functions_logs_bindings import (
    resolve_workflow_logs,
)


class StepFunctionsLogsHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        request = resolve_workflow_logs(connection, project)
        name = connection.source_name
        target = connection.target_name
        self._find_instance(name, project).config._cloudwatch_logs = True
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=name,
                    name="workflow_logs",
                    type="object({ arn = string, log_group_class = string, level = string, include_execution_data = bool })",
                    value=self._renderer.render_expression(
                        {
                            "arn": Expr(f"module.{target}.log_group_arn"),
                            "log_group_class": Expr(f"module.{target}.log_group_class"),
                            "level": request.level,
                            "include_execution_data": request.include_execution_data,
                        }
                    ),
                    description="Native execution-log destination and delivery settings",
                )
            ],
            outputs=[
                self._output(
                    target,
                    "log_group_class",
                    f"aws_cloudwatch_log_group.{target}.log_group_class",
                    "Native CloudWatch log-group metadata",
                ),
                self._output(
                    name,
                    "execution_log_destination",
                    str(workflow_log_destination()),
                    "Managed execution-log delivery ARN",
                ),
            ],
            resources=[
                self._resource(
                    name, "execution_logs.tf", render_workflow_logs(self._renderer)
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_workflow_logs(connection, project)
        return [
            *external_service_key_issues(connection, project),
            ConnectionIssue(
                severity="warning",
                message="The workflow logs selected execution events to the connected group through its existing external execution role. The generated inline policy scopes stream writes to that group; log-delivery management, discovery, and resource-policy APIs require wildcard resources and permit wider account operations. The deployment identity must read the role with iam:GetRole, attach inline policies, and pass it to Step Functions; role trust and permission boundaries remain external prerequisites. Terraform verifies the role's full native ARN before policy attachment. AWS manages the delivery resource policy; account policy size and delivery quotas still apply, and /aws/vendedlogs/states/ group names help avoid policy size limits. Payload logging is off by default; enabling it can expose secret values and state inputs/outputs. Express workflows have no Step Functions execution history, delivery is best effort, and oversized payloads can be truncated. Retention and log encryption belong to CloudWatch; external keys must authorize the regional Logs service. State-machine customer-key encryption is separate and is not configured. Log ingestion and storage incur charges.",
            ),
        ]
