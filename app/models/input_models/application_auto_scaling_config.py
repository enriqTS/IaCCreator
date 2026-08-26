"""Application Auto Scaling target configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class ApplicationAutoScalingConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.APPLICATION_AUTO_SCALING] = (
        ServiceType.APPLICATION_AUTO_SCALING
    )
    service_namespace: str = TerraformField(
        "ecs",
        description="AWS service namespace",
        options=[
            OptionEntry(value=value, label=value.upper())
            for value in ("ecs", "dynamodb", "lambda")
        ],
    )
    resource_id: str = TerraformField("", description="Scalable resource identifier")
    scalable_dimension: str = TerraformField(
        "ecs:service:DesiredCount",
        description="Scalable property dimension",
    )
    min_capacity: int = TerraformField(
        1, description="Minimum capacity", validation=ValidationRule(min=0)
    )
    max_capacity: int = TerraformField(
        10, description="Maximum capacity", validation=ValidationRule(min=1)
    )
    create_target_tracking_policy: bool = TerraformField(
        True, description="Create a target tracking scaling policy"
    )
    predefined_metric_type: str = TerraformField(
        "ECSServiceAverageCPUUtilization",
        description="Predefined target tracking metric",
        options=[
            OptionEntry(
                value="ECSServiceAverageCPUUtilization", label="ECS average CPU"
            ),
            OptionEntry(
                value="ECSServiceAverageMemoryUtilization", label="ECS average memory"
            ),
            OptionEntry(
                value="DynamoDBReadCapacityUtilization", label="DynamoDB read capacity"
            ),
            OptionEntry(
                value="DynamoDBWriteCapacityUtilization",
                label="DynamoDB write capacity",
            ),
            OptionEntry(
                value="LambdaProvisionedConcurrencyUtilization",
                label="Lambda provisioned concurrency",
            ),
        ],
    )
    target_value: float = TerraformField(
        70.0, description="Metric target value", validation=ValidationRule(min=0.1)
    )
    scale_in_cooldown: int = TerraformField(
        300,
        description="Scale-in cooldown in seconds",
        validation=ValidationRule(min=0),
    )
    scale_out_cooldown: int = TerraformField(
        300,
        description="Scale-out cooldown in seconds",
        validation=ValidationRule(min=0),
    )
