"""Bedrock-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class BedrockConfig(BaseServiceConfig):
    """Bedrock-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.BEDROCK] = ServiceType.BEDROCK

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "model_name",
        "base_model_identifier",
        "role_arn",
        "training_data_s3_uri",
        "output_data_s3_uri",
        "hyperparameters",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    model_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the custom model",
    )
    base_model_identifier: str | None = TerraformField(
        None,
        group="General",
        description="Base model identifier for customization",
        options=[
            OptionEntry(
                value="amazon.titan-text-express-v1",
                label="Amazon Titan Text Express",
            ),
            OptionEntry(
                value="amazon.titan-embed-text-v1", label="Amazon Titan Embed Text"
            ),
            OptionEntry(value="anthropic.claude-v2", label="Anthropic Claude v2"),
            OptionEntry(
                value="meta.llama2-13b-chat-v1", label="Meta Llama 2 13B Chat"
            ),
        ],
    )
    role_arn: str | None = TerraformField(
        None,
        group="General",
        description="IAM role ARN for Bedrock",
    )

    # ── Training ──────────────────────────────────────────────────────────
    training_data_s3_uri: str | None = TerraformField(
        None,
        group="Training",
        description="S3 URI of the training data",
        validation=ValidationRule(
            pattern="^s3://",
            pattern_description="Must be an S3 URI starting with s3://",
        ),
    )
    output_data_s3_uri: str | None = TerraformField(
        None,
        group="Training",
        description="S3 URI for the output data",
        validation=ValidationRule(
            pattern="^s3://",
            pattern_description="Must be an S3 URI starting with s3://",
        ),
    )
    hyperparameters: dict[str, str] | None = TerraformField(
        None,
        group="Training",
        description="Key-value pairs for training hyperparameters such as epoch count, batch size, and learning rate",
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="String key-value pairs for resource tagging",
    )
