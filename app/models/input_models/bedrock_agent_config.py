"""Bedrock Agent-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class BedrockAgentConfig(BaseServiceConfig):
    """Bedrock Agent-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.BEDROCK_AGENT] = ServiceType.BEDROCK_AGENT

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "agent_name",
        "foundation_model",
        "description",
        "instruction",
        "agent_resource_role_arn",
        "idle_session_ttl_in_seconds",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    agent_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Bedrock Agent",
    )
    foundation_model: str | None = TerraformField(
        None,
        group="General",
        description="Foundation model identifier for the agent",
        options=[
            OptionEntry(value="anthropic.claude-v2", label="Anthropic Claude v2"),
            OptionEntry(
                value="anthropic.claude-3-sonnet-20240229-v1:0",
                label="Anthropic Claude 3 Sonnet",
            ),
            OptionEntry(
                value="anthropic.claude-3-haiku-20240307-v1:0",
                label="Anthropic Claude 3 Haiku",
            ),
            OptionEntry(
                value="amazon.titan-text-express-v1",
                label="Amazon Titan Text Express",
            ),
            OptionEntry(
                value="meta.llama3-8b-instruct-v1:0",
                label="Meta Llama 3 8B Instruct",
            ),
        ],
    )
    description: str | None = TerraformField(
        None,
        group="General",
        description="Description of the Bedrock Agent",
    )
    instruction: str | None = TerraformField(
        None,
        group="General",
        description="Instruction for the Bedrock Agent",
    )
    agent_resource_role_arn: str | None = TerraformField(
        None,
        group="General",
        description="IAM role ARN for the Bedrock Agent",
    )

    # ── Configuration ─────────────────────────────────────────────────────
    idle_session_ttl_in_seconds: int | None = TerraformField(
        600,
        group="Configuration",
        description="Idle session timeout in seconds",
        validation=ValidationRule(min=60, max=3600),
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the Bedrock Agent",
    )
