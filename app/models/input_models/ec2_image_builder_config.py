"""EC2 Image Builder-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class Ec2ImageBuilderConfig(BaseServiceConfig):
    """EC2 Image Builder-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.EC2_IMAGE_BUILDER] = ServiceType.EC2_IMAGE_BUILDER

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "pipeline_name",
        "image_recipe_arn",
        "infrastructure_configuration_arn",
    )

    # ── General ───────────────────────────────────────────────────────────
    pipeline_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Image Builder pipeline",
    )
    image_recipe_arn: str | None = TerraformField(
        None,
        group="General",
        description="ARN of the image recipe",
    )
    infrastructure_configuration_arn: str | None = TerraformField(
        None,
        group="General",
        description="ARN of the infrastructure configuration",
    )
