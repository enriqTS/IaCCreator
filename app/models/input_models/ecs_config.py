"""ECS-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class EcsConfig(BaseServiceConfig):
    """ECS-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.ECS] = ServiceType.ECS

    owns_execution_role: ClassVar[bool] = True
    execution_role_principal: ClassVar[str] = "ecs-tasks.amazonaws.com"

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_name",
        "task_family",
        "ecs_cpu",
        "ecs_memory",
    )

    # ── General ───────────────────────────────────────────────────────────
    cluster_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the ECS cluster",
    )
    task_family: str | None = TerraformField(
        None,
        group="General",
        description="Family name for the ECS task definition",
    )

    # ── Performance ───────────────────────────────────────────────────────
    ecs_cpu: str | None = TerraformField(
        "256",
        group="Performance",
        description="CPU units for the ECS task",
    )
    ecs_memory: str | None = TerraformField(
        "512",
        group="Performance",
        description="Memory (MiB) for the ECS task",
    )

    # ── Internal (not Terraform variables) ────────────────────────────────
    ecs_launch_type: str | None = None
    ecs_desired_count: int | None = None
    ecs_load_balancers: list[dict[str, str | int]] = []

    @classmethod
    def execution_role_base_statements(cls, instance_name: str) -> list[dict]:
        """Every task needs to pull its image and write its logs."""
        return [
            {
                "Effect": "Allow",
                "Action": [
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": "*",
            }
        ]
