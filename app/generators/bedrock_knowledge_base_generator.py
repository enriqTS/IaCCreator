"""Bedrock Knowledge Base generator — produces HCL for aws_bedrockagent_knowledge_base resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.generators.variable_schemas import VARIABLE_SCHEMAS
from app.models.input_models import ServiceType
from app.models.ir_models import ResourceInstanceIR


class BedrockKnowledgeBaseGenerator:
    """Generates Terraform files for Bedrock Knowledge Base resources."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_bedrockagent_knowledge_base resource."""
        attrs: dict = {
            "name": "var.knowledge_base_name",
            "description": "var.description",
            "role_arn": "var.role_arn",
            "knowledge_base_configuration": {
                "type": "VECTOR",
                "vector_knowledge_base_configuration": {
                    "embedding_model_arn": "var.embedding_model_arn",
                },
            },
            "storage_configuration": {
                "type": "var.storage_type",
                "opensearch_serverless_configuration": {
                    "vector_index_name": "var.vector_field",
                    "field_mapping": {
                        "vector_field": "var.vector_field",
                        "text_field": "var.text_field",
                        "metadata_field": "var.metadata_field",
                    },
                },
            },
            "tags": "var.tags",
        }
        return self._r.render_resource(
            "aws_bedrockagent_knowledge_base", instance.name, attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf dynamically from VARIABLE_SCHEMAS."""
        schema = VARIABLE_SCHEMAS[ServiceType.BEDROCK_KNOWLEDGE_BASE]
        parts = []
        for entry in schema:
            tf_type = "map(string)" if entry.type == "map" else entry.type
            parts.append(
                self._r.render_variable(
                    entry.name, tf_type, entry.description, entry.default
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Bedrock Knowledge Base."""
        parts = [
            self._r.render_output(
                "knowledge_base_id",
                f"aws_bedrockagent_knowledge_base.{instance.name}.id",
                "ID of the Bedrock Knowledge Base",
            ),
            self._r.render_output(
                "knowledge_base_arn",
                f"aws_bedrockagent_knowledge_base.{instance.name}.arn",
                "ARN of the Bedrock Knowledge Base",
            ),
        ]
        return "\n".join(parts)
