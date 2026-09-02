"""Lambda target attachments owned by target-group modules."""

from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.input_models.target_group_config import TargetGroupConfig
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class TargetGroupLambdaAttachmentHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        function = safe_identifier(connection.target_name)
        arn_variable = f"{function}_function_arn"
        name_variable = f"{function}_function_name"
        attachment = self._renderer.render_resource(
            "aws_lb_target_group_attachment",
            f"{function}_attachment",
            {
                "target_group_arn": Expr(
                    f"aws_lb_target_group.{connection.source_name}.arn"
                ),
                "target_id": Expr(f"var.{arn_variable}"),
                "depends_on": Expr(f"[aws_lambda_permission.{function}_permission]"),
            },
        )
        permission = self._renderer.render_resource(
            "aws_lambda_permission",
            f"{function}_permission",
            {
                "statement_id": f"AllowExecutionFromTargetGroup{function}",
                "action": "lambda:InvokeFunction",
                "function_name": Expr(f"var.{name_variable}"),
                "principal": "elasticloadbalancing.amazonaws.com",
                "source_arn": Expr(f"aws_lb_target_group.{connection.source_name}.arn"),
            },
        )
        return ConnectionContribution(
            inputs=[
                self._input(
                    connection.source_name,
                    connection.target_name,
                    "function_arn",
                    f"module.{connection.target_name}.function_arn",
                    "Lambda ARN registered with this target group",
                ),
                self._input(
                    connection.source_name,
                    connection.target_name,
                    "function_name",
                    f"module.{connection.target_name}.function_name",
                    "Lambda name granted invocation permission",
                ),
            ],
            resources=[
                self._resource(
                    connection.source_name,
                    f"attachment_{function}.tf",
                    attachment,
                ),
                self._resource(
                    connection.source_name,
                    f"permission_{function}.tf",
                    permission,
                ),
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        group = self._find_instance(connection.source_name, project)
        if group is None or not isinstance(group.config, TargetGroupConfig):
            return []
        if group.config.target_type != "lambda":
            return [
                ConnectionIssue(
                    severity="error",
                    message="Lambda attachments require a lambda target group",
                )
            ]
        return []
