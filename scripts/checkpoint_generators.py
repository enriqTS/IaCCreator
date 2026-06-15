"""Checkpoint script: verify all 6 AI service generators import correctly and produce valid output."""

import sys

from app.generators.bedrock_generator import BedrockGenerator
from app.generators.sagemaker_generator import SageMakerGenerator
from app.generators.amazon_q_generator import AmazonQGenerator
from app.generators.bedrock_agent_generator import BedrockAgentGenerator
from app.generators.bedrock_knowledge_base_generator import BedrockKnowledgeBaseGenerator
from app.generators.bedrock_guardrail_generator import BedrockGuardrailGenerator
from app.models.ir_models import ResourceInstanceIR
from app.models.input_models import ServiceType, ResourceConfig


def make_instance(name: str, service_type: ServiceType) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for testing."""
    return ResourceInstanceIR(
        name=name,
        service_type=service_type,
        config=ResourceConfig(),
    )


def check_generator(generator_cls, service_type: ServiceType, name: str, expected_keywords: dict):
    """Run the 3 generation methods and verify expected keywords in output."""
    gen = generator_cls()
    instance = make_instance(name, service_type)

    resource_tf = gen.generate_resource_tf(instance)
    variables_tf = gen.generate_variables_tf(instance)
    outputs_tf = gen.generate_outputs_tf(instance)

    errors = []

    # Check non-empty
    if not resource_tf.strip():
        errors.append(f"  generate_resource_tf returned empty string")
    if not variables_tf.strip():
        errors.append(f"  generate_variables_tf returned empty string")
    if not outputs_tf.strip():
        errors.append(f"  generate_outputs_tf returned empty string")

    # Check expected keywords in resource_tf
    for kw in expected_keywords.get("resource", []):
        if kw not in resource_tf:
            errors.append(f"  resource_tf missing keyword: '{kw}'")

    # Check expected keywords in variables_tf
    for kw in expected_keywords.get("variables", []):
        if kw not in variables_tf:
            errors.append(f"  variables_tf missing keyword: '{kw}'")

    # Check expected keywords in outputs_tf
    for kw in expected_keywords.get("outputs", []):
        if kw not in outputs_tf:
            errors.append(f"  outputs_tf missing keyword: '{kw}'")

    return errors


def main():
    all_passed = True
    generators = [
        (
            "BedrockGenerator",
            BedrockGenerator,
            ServiceType.BEDROCK,
            "my_bedrock",
            {
                "resource": ["aws_bedrock_custom_model", "my_bedrock", "var.model_name"],
                "variables": ["model_name", "base_model_identifier", "role_arn"],
                "outputs": ["model_arn", "aws_bedrock_custom_model.my_bedrock"],
            },
        ),
        (
            "SageMakerGenerator",
            SageMakerGenerator,
            ServiceType.SAGEMAKER,
            "my_sagemaker",
            {
                "resource": ["aws_sagemaker_notebook_instance", "my_sagemaker", "var.notebook_instance_name"],
                "variables": ["notebook_instance_name", "instance_type", "role_arn"],
                "outputs": ["notebook_instance_arn", "aws_sagemaker_notebook_instance.my_sagemaker"],
            },
        ),
        (
            "AmazonQGenerator",
            AmazonQGenerator,
            ServiceType.AMAZON_Q,
            "my_q_app",
            {
                "resource": ["aws_qbusiness_application", "my_q_app", "var.application_name"],
                "variables": ["application_name", "description", "role_arn"],
                "outputs": ["application_id", "aws_qbusiness_application.my_q_app"],
            },
        ),
        (
            "BedrockAgentGenerator",
            BedrockAgentGenerator,
            ServiceType.BEDROCK_AGENT,
            "my_agent",
            {
                "resource": ["aws_bedrockagent_agent", "my_agent", "var.agent_name"],
                "variables": ["agent_name", "foundation_model", "instruction", "agent_resource_role_arn"],
                "outputs": ["agent_id", "aws_bedrockagent_agent.my_agent"],
            },
        ),
        (
            "BedrockKnowledgeBaseGenerator",
            BedrockKnowledgeBaseGenerator,
            ServiceType.BEDROCK_KNOWLEDGE_BASE,
            "my_kb",
            {
                "resource": ["aws_bedrockagent_knowledge_base", "my_kb", "var.knowledge_base_name", "var.role_arn"],
                "variables": ["knowledge_base_name", "description", "role_arn", "embedding_model_arn"],
                "outputs": ["knowledge_base_id", "aws_bedrockagent_knowledge_base.my_kb"],
            },
        ),
        (
            "BedrockGuardrailGenerator",
            BedrockGuardrailGenerator,
            ServiceType.BEDROCK_GUARDRAIL,
            "my_guardrail",
            {
                "resource": ["aws_bedrock_guardrail", "my_guardrail", "var.guardrail_name"],
                "variables": ["guardrail_name", "description", "blocked_input_messaging", "blocked_outputs_messaging"],
                "outputs": ["guardrail_id", "aws_bedrock_guardrail.my_guardrail"],
            },
        ),
    ]

    print("=" * 60)
    print("Checkpoint: Verifying all 6 AI service generators")
    print("=" * 60)

    for label, cls, stype, name, keywords in generators:
        errors = check_generator(cls, stype, name, keywords)
        if errors:
            print(f"\n❌ FAIL: {label}")
            for e in errors:
                print(e)
            all_passed = False
        else:
            print(f"✅ PASS: {label}")

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL 6 GENERATORS PASSED CHECKPOINT ✅")
        print("=" * 60)
        sys.exit(0)
    else:
        print("SOME GENERATORS FAILED CHECKPOINT ❌")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
