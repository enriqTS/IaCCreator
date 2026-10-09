"""Experiment-owned ECS selectors leave task definitions and services intact."""

from app.generators.fis_ecs import render_ecs_fault_policy
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
from app.services.connection_handlers.fis_ecs_bindings import resolve_ecs_fault


class FisEcsHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        binding = resolve_ecs_fault(connection, project)
        peers = [
            item
            for item in project.connections
            if item.source_name == connection.source_name
            and item.source_service == ServiceType.FAULT_INJECTION_SIMULATOR
            and item.target_service == ServiceType.ECS
            and item.connection_type == "targets"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        source, target = connection.source_name, binding.target
        self._find_instance(source, project).config._targets_ecs = True
        native_service = self._renderer.render_expression(
            {
                "cluster_arn": Expr(f"aws_ecs_cluster.{target}.arn"),
                "cluster_name": Expr(f"aws_ecs_cluster.{target}.name"),
                "service_arn": Expr(f"aws_ecs_service.{target}_service.id"),
                "service_name": Expr(f"aws_ecs_service.{target}_service.name"),
            }
        )
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source,
                    name="fis_ecs_service",
                    type="object({ cluster_arn = string, cluster_name = string, service_arn = string, service_name = string })",
                    value=f"module.{target}.fis_service",
                    description="Native ECS service and owning cluster",
                ),
                ModuleInput(
                    module=source,
                    name="fis_ecs_selection",
                    type="string",
                    value=self._renderer.render_expression(binding.selection_mode),
                    description="Running task selection resolved at experiment execution",
                ),
            ],
            outputs=[
                self._output(
                    target,
                    "fis_service",
                    native_service,
                    "Native service selector for ECS fault experiments",
                ),
                self._output(
                    source,
                    "ecs_target",
                    "merge(var.fis_ecs_service, { selection_mode = var.fis_ecs_selection })",
                    "ECS service selector and running task selection",
                ),
            ],
            resources=[
                self._resource(
                    source, "ecs_targets.tf", render_ecs_fault_policy(self._renderer)
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        binding = resolve_ecs_fault(connection, project)
        return [
            ConnectionIssue(
                severity="warning",
                message=f"This connection creates an ECS stop-task template with {binding.selection_mode} selection among running tasks in the connected service; Terraform does not start experiments. The connection selects aws:ecs:stop-task instead of standalone action_id. Each template supports one ECS service and cannot mix EC2 and ECS targets. The external role must trust fis.amazonaws.com with suitable source-account/experiment-ARN restrictions; the deployment identity needs iam:GetRole, inline-policy management, and iam:PassRole. Native cluster/service identity and the exact role ARN are checked before policy attachment. StopTask and DescribeTasks permissions cover tasks throughout the connected cluster, including other services or standalone tasks; the template's service selector is not an IAM boundary. ListTasks uses wildcard resources with a cluster condition, and tag discovery is regional. Shared roles retain existing permissions. AWS resolves eligible tasks at experiment execution; zero matches or an unavailable selection count can fail the experiment, and ALL follows the current service scale. Stopping a task stops all its containers and can interrupt requests or lose ephemeral data; the ECS scheduler may replace service tasks according to desired count and available capacity. The template retains source=none stop conditions; alarm-based stops, recovery verification, SSM sidecars, and stress/network faults are not configured. Check service capacity, replacement health, and costs before execution.",
            )
        ]
