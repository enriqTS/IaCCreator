"""Amazon Q-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class AmazonQConfig(BaseServiceConfig):
    """Amazon Q-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.AMAZON_Q] = ServiceType.AMAZON_Q

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "application_name",
        "description",
        "identity_type",
        "role_arn",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    application_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Amazon Q application",
    )
    description: str | None = TerraformField(
        None,
        group="General",
        description="Description of the Amazon Q application",
    )
    identity_type: str | None = TerraformField(
        None,
        group="General",
        description="Identity provider type for the Amazon Q application",
        options=[
            OptionEntry(value="AWS_IAM_IDP", label="AWS IAM Identity Provider"),
            OptionEntry(value="AWS_IAM_IC", label="AWS IAM Identity Center"),
            OptionEntry(value="AWS_QUICKSIGHT", label="Amazon QuickSight"),
        ],
    )
    role_arn: str | None = TerraformField(
        None,
        group="General",
        description="IAM role ARN for the Amazon Q application",
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the Amazon Q application",
    )
