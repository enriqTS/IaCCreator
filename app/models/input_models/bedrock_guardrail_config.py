"""Bedrock Guardrail-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class BedrockGuardrailConfig(BaseServiceConfig):
    """Bedrock Guardrail-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.BEDROCK_GUARDRAIL] = ServiceType.BEDROCK_GUARDRAIL

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "guardrail_name",
        "description",
        "blocked_input_messaging",
        "blocked_outputs_messaging",
        "content_policy_strength",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    guardrail_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Bedrock Guardrail",
    )
    description: str | None = TerraformField(
        None,
        group="General",
        description="Description of the guardrail",
    )
    blocked_input_messaging: str | None = TerraformField(
        None,
        group="General",
        description="Message to return when input is blocked",
    )
    blocked_outputs_messaging: str | None = TerraformField(
        None,
        group="General",
        description="Message to return when output is blocked",
    )

    # ── Content Policy ────────────────────────────────────────────────────
    content_policy_strength: str | None = TerraformField(
        "MEDIUM",
        group="Content Policy",
        description="Content filtering strength level",
        options=[
            OptionEntry(value="NONE", label="None"),
            OptionEntry(value="LOW", label="Low"),
            OptionEntry(value="MEDIUM", label="Medium"),
            OptionEntry(value="HIGH", label="High"),
        ],
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the Bedrock Guardrail",
    )
