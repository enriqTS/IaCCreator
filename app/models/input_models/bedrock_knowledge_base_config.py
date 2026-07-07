"""Bedrock Knowledge Base-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class BedrockKnowledgeBaseConfig(BaseServiceConfig):
    """Bedrock Knowledge Base-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.BEDROCK_KNOWLEDGE_BASE] = (
        ServiceType.BEDROCK_KNOWLEDGE_BASE
    )

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "knowledge_base_name",
        "description",
        "role_arn",
        "embedding_model_arn",
        "storage_type",
        "vector_field",
        "text_field",
        "metadata_field",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    knowledge_base_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the knowledge base",
    )
    description: str | None = TerraformField(
        None,
        group="General",
        description="Description of the knowledge base",
    )
    role_arn: str | None = TerraformField(
        None,
        group="General",
        description="IAM role ARN for the knowledge base",
    )
    embedding_model_arn: str | None = TerraformField(
        None,
        group="General",
        description="ARN of the embedding model for vector indexing",
        options=[
            OptionEntry(
                value="amazon.titan-embed-text-v1",
                label="Titan Embeddings G1 - Text",
            ),
            OptionEntry(
                value="amazon.titan-embed-text-v2:0",
                label="Titan Embeddings G1 - Text v2",
            ),
            OptionEntry(
                value="cohere.embed-english-v3", label="Cohere Embed English v3"
            ),
        ],
    )

    # ── Storage Configuration ─────────────────────────────────────────────
    storage_type: str | None = TerraformField(
        "OPENSEARCH_SERVERLESS",
        group="Storage Configuration",
        description="Vector storage type for the knowledge base",
        options=[
            OptionEntry(value="OPENSEARCH_SERVERLESS", label="OpenSearch Serverless"),
            OptionEntry(value="PINECONE", label="Pinecone"),
            OptionEntry(value="RDS", label="RDS Aurora PostgreSQL"),
        ],
    )
    vector_field: str | None = TerraformField(
        None,
        group="Storage Configuration",
        description="Name of the vector field in the storage",
    )
    text_field: str | None = TerraformField(
        None,
        group="Storage Configuration",
        description="Name of the text field in the storage",
    )
    metadata_field: str | None = TerraformField(
        None,
        group="Storage Configuration",
        description="Name of the metadata field in the storage",
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the Bedrock Knowledge Base",
    )
