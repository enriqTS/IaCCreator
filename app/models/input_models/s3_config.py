"""S3-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class S3Config(BaseServiceConfig):
    """S3-specific configuration."""

    service_type: Literal[ServiceType.S3] = ServiceType.S3

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "bucket_name",
        "versioning",
        "force_destroy",
        "object_lock_enabled",
        "acceleration_status",
        "tags",
    )

    # General
    bucket_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the S3 bucket",
    )
    versioning: str | None = TerraformField(
        "Enabled",
        group="General",
        description="Versioning status for the S3 bucket",
        options=[
            OptionEntry(value="Enabled", label="Enabled"),
            OptionEntry(value="Suspended", label="Suspended"),
            OptionEntry(value="Disabled", label="Disabled"),
        ],
    )

    # Configuration
    force_destroy: bool | None = TerraformField(
        False,
        group="Configuration",
        description="Allow deletion of non-empty bucket by deleting all objects",
    )
    object_lock_enabled: bool | None = TerraformField(
        False,
        group="Configuration",
        description="Enable S3 Object Lock on the bucket",
    )
    acceleration_status: str | None = TerraformField(
        None,
        group="Configuration",
        description="Transfer acceleration status for the bucket",
        options=[
            OptionEntry(value="Enabled", label="Enabled"),
            OptionEntry(value="Suspended", label="Suspended"),
        ],
    )

    # Metadata
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the S3 bucket",
        tf_type="map",
    )
