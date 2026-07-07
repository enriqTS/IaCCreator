"""CloudWatch-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class CloudWatchConfig(BaseServiceConfig):
    """CloudWatch-specific configuration."""

    service_type: Literal[ServiceType.CLOUDWATCH] = ServiceType.CLOUDWATCH

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "log_group_name",
        "retention_in_days",
        "kms_key_id",
        "log_group_class",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    log_group_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the CloudWatch log group",
    )
    retention_in_days: int | None = TerraformField(
        30,
        group="General",
        description="Number of days to retain log events",
        options=[
            OptionEntry(value=0, label="Never expire"),
            OptionEntry(value=1, label="1 day"),
            OptionEntry(value=3, label="3 days"),
            OptionEntry(value=5, label="5 days"),
            OptionEntry(value=7, label="1 week"),
            OptionEntry(value=14, label="2 weeks"),
            OptionEntry(value=30, label="1 month"),
            OptionEntry(value=60, label="2 months"),
            OptionEntry(value=90, label="3 months"),
            OptionEntry(value=120, label="4 months"),
            OptionEntry(value=150, label="5 months"),
            OptionEntry(value=180, label="6 months"),
            OptionEntry(value=365, label="1 year"),
            OptionEntry(value=400, label="13 months"),
            OptionEntry(value=545, label="18 months"),
            OptionEntry(value=731, label="2 years"),
            OptionEntry(value=1096, label="3 years"),
            OptionEntry(value=1827, label="5 years"),
            OptionEntry(value=2192, label="6 years"),
            OptionEntry(value=2557, label="7 years"),
            OptionEntry(value=2922, label="8 years"),
            OptionEntry(value=3288, label="9 years"),
            OptionEntry(value=3653, label="10 years"),
        ],
        validation=ValidationRule(
            allowed_values=[
                0,
                1,
                3,
                5,
                7,
                14,
                30,
                60,
                90,
                120,
                150,
                180,
                365,
                400,
                545,
                731,
                1096,
                1827,
                2192,
                2557,
                2922,
                3288,
                3653,
            ],
        ),
    )

    # ── Configuration ─────────────────────────────────────────────────────
    kms_key_id: str | None = TerraformField(
        None,
        group="Configuration",
        description="ARN of the KMS key to use for encrypting log data",
    )
    log_group_class: str | None = TerraformField(
        "STANDARD",
        group="Configuration",
        description="Log group class for the CloudWatch log group",
        options=[
            OptionEntry(value="STANDARD", label="Standard"),
            OptionEntry(value="INFREQUENT_ACCESS", label="Infrequent Access"),
        ],
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the CloudWatch log group",
        tf_type="map",
    )
