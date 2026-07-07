"""Elastic Beanstalk-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class ElasticBeanstalkConfig(BaseServiceConfig):
    """Elastic Beanstalk-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.ELASTIC_BEANSTALK] = ServiceType.ELASTIC_BEANSTALK

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "application_name",
        "environment_name",
    )

    # ── General ───────────────────────────────────────────────────────────
    application_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Elastic Beanstalk application",
    )
    environment_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Elastic Beanstalk environment",
    )

    # ── Internal (not Terraform variables) ────────────────────────────────
    eb_solution_stack_name: str | None = None
    eb_tier: str | None = None
