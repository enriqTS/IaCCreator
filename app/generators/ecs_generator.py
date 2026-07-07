"""ECS service generator — produces HCL for ECS cluster, task definition, and service resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class ECSGenerator:
    """Generates Terraform files for ECS clusters, task definitions, and services."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_ecs_cluster, aws_ecs_task_definition, and aws_ecs_service."""
        # ECS Cluster
        cluster_attrs: dict = {"name": "var.cluster_name"}
        result = self._r.render_resource(
            "aws_ecs_cluster", instance.name, cluster_attrs
        )

        # ECS Task Definition
        task_attrs: dict = {
            "family": "var.task_family",
            "cpu": "var.ecs_cpu",
            "memory": "var.ecs_memory",
            "network_mode": "awsvpc",
            "requires_compatibilities": ["FARGATE"],
        }
        result += "\n" + self._r.render_resource(
            "aws_ecs_task_definition", f"{instance.name}_task", task_attrs
        )

        # ECS Service
        service_attrs: dict = {
            "name": "var.cluster_name",
            "cluster": f"aws_ecs_cluster.{instance.name}.id",
            "task_definition": f"aws_ecs_task_definition.{instance.name}_task.arn",
        }
        if instance.config.ecs_launch_type is not None:
            service_attrs["launch_type"] = "var.ecs_launch_type"
        if instance.config.ecs_desired_count is not None:
            service_attrs["desired_count"] = "var.ecs_desired_count"

        result += "\n" + self._r.render_resource(
            "aws_ecs_service", f"{instance.name}_service", service_attrs
        )

        return result

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an ECS instance."""
        parts = [
            self._r.render_variable(
                "cluster_name", "string", "Name of the ECS cluster"
            ),
            self._r.render_variable(
                "task_family", "string", "Family name for the ECS task definition"
            ),
            self._r.render_variable("ecs_cpu", "string", "CPU units for the ECS task"),
            self._r.render_variable(
                "ecs_memory", "string", "Memory (MiB) for the ECS task"
            ),
        ]
        if instance.config.ecs_launch_type is not None:
            parts.append(
                self._r.render_variable(
                    "ecs_launch_type",
                    "string",
                    "Launch type for the ECS service",
                    default=instance.config.ecs_launch_type,
                )
            )
        if instance.config.ecs_desired_count is not None:
            parts.append(
                self._r.render_variable(
                    "ecs_desired_count",
                    "number",
                    "Desired number of tasks in the ECS service",
                    default=instance.config.ecs_desired_count,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an ECS instance."""
        parts = [
            self._r.render_output(
                "cluster_arn",
                f"aws_ecs_cluster.{instance.name}.arn",
                "ARN of the ECS cluster",
            ),
            self._r.render_output(
                "service_name",
                f"aws_ecs_service.{instance.name}_service.name",
                "Name of the ECS service",
            ),
        ]
        return "\n".join(parts)
