"""Experiment-owned target bindings never execute faults during generation."""

from app.generators.fis_ec2 import render_ec2_fault_policy
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.fis_ec2_bindings import resolve_ec2_fault


class FisEc2Handler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        binding = resolve_ec2_fault(connection, project)
        peers = [
            item
            for item in project.connections
            if item.source_name == connection.source_name
            and item.source_service == ServiceType.FAULT_INJECTION_SIMULATOR
            and item.target_service == ServiceType.EC2
            and item.connection_type == "targets"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        source = connection.source_name
        self._find_instance(source, project).config._target_service = ServiceType.EC2
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source,
                    name="fis_ec2_targets",
                    type="map(object({ arn = string, can_stop = bool }))",
                    value=self._renderer.render_expression(
                        {
                            name: Expr(f"module.{name}.fis_instance")
                            for name in binding.targets
                        }
                    ),
                    description="Native explicitly connected EC2 targets",
                ),
                ModuleInput(
                    module=source,
                    name="fis_ec2_action",
                    type="object({ operation = string, selection_mode = string })",
                    value=self._renderer.render_expression(
                        {
                            "operation": binding.operation,
                            "selection_mode": binding.selection_mode,
                        }
                    ),
                    description="Managed EC2 fault operation and target selection",
                ),
            ],
            outputs=[
                *[
                    self._output(
                        name,
                        "fis_instance",
                        self._renderer.render_expression(
                            {
                                "arn": Expr(f"aws_instance.{name}.arn"),
                                "can_stop": Expr(
                                    f"length(aws_instance.{name}.root_block_device) > 0 && !coalesce(aws_instance.{name}.disable_api_stop, false)"
                                ),
                            }
                        ),
                        "Native EC2 experiment target and stop capability",
                    )
                    for name in binding.targets
                ],
                self._output(
                    source,
                    "ec2_target_arns",
                    "local.fis_ec2_arns",
                    "Explicit EC2 instance ARNs eligible for the experiment",
                ),
            ],
            resources=[
                self._resource(
                    source, "ec2_targets.tf", render_ec2_fault_policy(self._renderer)
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        binding = resolve_ec2_fault(connection, project)
        return [
            ConnectionIssue(
                severity="warning",
                message=f"This connection creates a {binding.operation} experiment template with explicit EC2 targets and {binding.selection_mode} selection; Terraform does not start experiments. The connection selects the action instead of the standalone action_id field. All target connections in the template share that operation and selection. The external role must trust fis.amazonaws.com with suitable source-account/experiment-ARN restrictions; the deployment identity needs iam:GetRole, inline-policy management, and iam:PassRole. Terraform checks the full role ARN before policy attachment. The generated policy scopes reboot or AWS-required stop/start permissions to connected instances, plus regional wildcard instance discovery; shared roles retain all their existing permissions. Instances must be running and eligible when an operator starts an experiment; stop operations require an EBS-backed root without stop protection and leave instances stopped until manually restarted. The template retains source=none stop conditions; alarm-based automatic stops and automatic restart/KMS grant management are not configured. Plan workload recovery, instance-store data loss during stop, permissions to start encrypted instances, and experiment charges before execution.",
            )
        ]
