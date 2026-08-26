"""Load balancer target group configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
    VisibleWhen,
)


class TargetGroupConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.TARGET_GROUP] = ServiceType.TARGET_GROUP
    target_group_name: str = TerraformField(
        "target-group", description="Target group name"
    )
    vpc_id: str = TerraformField("", description="VPC ID")
    port: int = TerraformField(
        80, description="Traffic port", validation=ValidationRule(min=1, max=65535)
    )
    protocol: str = TerraformField(
        "HTTP",
        description="Traffic protocol",
        options=[
            OptionEntry(value=value, label=value)
            for value in ("HTTP", "HTTPS", "TCP", "TLS", "UDP", "TCP_UDP", "GENEVE")
        ],
    )
    target_type: str = TerraformField(
        "instance",
        description="Target type",
        options=[
            OptionEntry(value=value, label=value.title())
            for value in ("instance", "ip")
        ],
    )
    health_check_path: str = TerraformField(
        "/",
        group="Health check",
        description="HTTP health check path",
        visible_when=VisibleWhen(field="protocol", equals="HTTP"),
    )
