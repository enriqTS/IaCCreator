"""Bedrock AgentCore-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class BedrockAgentcoreConfig(BaseServiceConfig):
    """Bedrock AgentCore-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.BEDROCK_AGENTCORE] = ServiceType.BEDROCK_AGENTCORE

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "agent_runtime_name",
        "foundation_model",
        "role_arn",
        "description",
        "memory_id",
        "idle_session_ttl",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    agent_runtime_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the AgentCore runtime",
    )
    foundation_model: str | None = TerraformField(
        None,
        group="General",
        description="Foundation model for the agent runtime",
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
    role_arn: str | None = TerraformField(
        None,
        group="General",
        description="IAM role ARN for the AgentCore runtime",
    )
    description: str | None = TerraformField(
        None,
        group="General",
        description="Description of the agent runtime",
    )

    # ── Configuration ─────────────────────────────────────────────────────
    memory_id: str | None = TerraformField(
        None,
        group="Configuration",
        description="Memory store identifier for session context",
    )
    idle_session_ttl: int | None = TerraformField(
        600,
        group="Configuration",
        description="Idle session timeout in seconds",
        validation=ValidationRule(min=60, max=3600),
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the AgentCore runtime",
    )
