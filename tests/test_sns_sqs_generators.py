"""Unit tests for SNS and SQS service generators.

Covers task 3.4 of the connection-aware-terraform-generation spec:
- SNSGenerator.generate_resource_tf produces valid aws_sns_topic HCL
- SNSGenerator with fifo_topic=True includes fifo_topic and content_based_deduplication
- SQSGenerator.generate_resource_tf produces valid aws_sqs_queue HCL
- SQSGenerator with fifo_queue=True includes fifo_queue and content_based_deduplication
- generate_variables_tf and generate_outputs_tf for both generators
- Both generators are registered in GENERATOR_REGISTRY
"""

from app.generators.registry import GENERATOR_REGISTRY
from app.generators.sns_generator import SNSGenerator
from app.generators.sqs_generator import SQSGenerator
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sns_instance(name: str = "my-topic", **config_kwargs) -> ResourceInstanceIR:
    """Build a ResourceInstanceIR for an SNS topic with optional config overrides."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.SNS,
        config=ResourceConfig(**config_kwargs),
    )


def _sqs_instance(name: str = "my-queue", **config_kwargs) -> ResourceInstanceIR:
    """Build a ResourceInstanceIR for an SQS queue with optional config overrides."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.SQS,
        config=ResourceConfig(**config_kwargs),
    )


# ===========================================================================
# 1. SNSGenerator — generate_resource_tf
# ===========================================================================

class TestSNSGeneratorResourceTf:
    """Test SNSGenerator.generate_resource_tf produces valid aws_sns_topic HCL."""

    def setup_method(self):
        self.gen = SNSGenerator()

    def test_minimal_sns_topic(self):
        """A minimal SNS topic produces an aws_sns_topic with only name."""
        instance = _sns_instance("notifications")
        hcl = self.gen.generate_resource_tf(instance)
        assert 'resource "aws_sns_topic" "notifications"' in hcl
        assert "name = var.topic_name" in hcl

    def test_sns_with_display_name(self):
        """When display_name is set, the HCL includes display_name attribute."""
        instance = _sns_instance(display_name="My Notifications")
        hcl = self.gen.generate_resource_tf(instance)
        assert "display_name = var.display_name" in hcl

    def test_sns_with_kms_master_key_id(self):
        """When kms_master_key_id is set, the HCL includes kms_master_key_id attribute."""
        instance = _sns_instance(kms_master_key_id="arn:aws:kms:us-east-1:123456789:key/abc")
        hcl = self.gen.generate_resource_tf(instance)
        assert "kms_master_key_id = var.kms_master_key_id" in hcl

    def test_sns_with_tags(self):
        """When tags are set, the HCL includes tags attribute."""
        instance = _sns_instance(tags={"env": "dev"})
        hcl = self.gen.generate_resource_tf(instance)
        assert "tags = var.tags" in hcl

    def test_sns_without_optional_attrs_excludes_them(self):
        """When optional attributes are not set, they are absent from HCL."""
        instance = _sns_instance()
        hcl = self.gen.generate_resource_tf(instance)
        assert "display_name" not in hcl
        assert "fifo_topic" not in hcl
        assert "content_based_deduplication" not in hcl
        assert "kms_master_key_id" not in hcl
        assert "tags" not in hcl


# ===========================================================================
# 2. SNSGenerator — FIFO topic
# ===========================================================================

class TestSNSGeneratorFifo:
    """Test SNSGenerator with fifo_topic=True includes fifo and deduplication."""

    def setup_method(self):
        self.gen = SNSGenerator()

    def test_fifo_topic_includes_fifo_attribute(self):
        """When fifo_topic=True, the HCL includes fifo_topic."""
        instance = _sns_instance(fifo_topic=True)
        hcl = self.gen.generate_resource_tf(instance)
        assert "fifo_topic = var.fifo_topic" in hcl

    def test_fifo_topic_with_deduplication(self):
        """When fifo_topic=True and content_based_deduplication=True, both appear."""
        instance = _sns_instance(fifo_topic=True, content_based_deduplication=True)
        hcl = self.gen.generate_resource_tf(instance)
        assert "fifo_topic = var.fifo_topic" in hcl
        assert "content_based_deduplication = var.content_based_deduplication" in hcl


# ===========================================================================
# 3. SNSGenerator — generate_variables_tf
# ===========================================================================

class TestSNSGeneratorVariablesTf:
    """Test SNSGenerator.generate_variables_tf produces correct variable blocks."""

    def setup_method(self):
        self.gen = SNSGenerator()

    def test_minimal_variables(self):
        """A minimal SNS instance produces a topic_name variable."""
        instance = _sns_instance()
        hcl = self.gen.generate_variables_tf(instance)
        assert 'variable "topic_name"' in hcl
        assert "type        = string" in hcl

    def test_variables_with_all_optional_fields(self):
        """When all optional fields are set, all corresponding variables appear."""
        instance = _sns_instance(
            display_name="My Topic",
            fifo_topic=True,
            content_based_deduplication=True,
            kms_master_key_id="arn:aws:kms:us-east-1:123:key/abc",
            tags={"env": "prod"},
        )
        hcl = self.gen.generate_variables_tf(instance)
        assert 'variable "topic_name"' in hcl
        assert 'variable "display_name"' in hcl
        assert 'variable "fifo_topic"' in hcl
        assert 'variable "content_based_deduplication"' in hcl
        assert 'variable "kms_master_key_id"' in hcl
        assert 'variable "tags"' in hcl

    def test_variables_include_defaults(self):
        """Variable blocks include default values from the config."""
        instance = _sns_instance(fifo_topic=True)
        hcl = self.gen.generate_variables_tf(instance)
        assert "default     = true" in hcl


# ===========================================================================
# 4. SNSGenerator — generate_outputs_tf
# ===========================================================================

class TestSNSGeneratorOutputsTf:
    """Test SNSGenerator.generate_outputs_tf produces topic_arn and topic_name outputs."""

    def setup_method(self):
        self.gen = SNSGenerator()

    def test_outputs_contain_topic_arn(self):
        """Outputs include topic_arn referencing the SNS topic ARN."""
        instance = _sns_instance("alerts")
        hcl = self.gen.generate_outputs_tf(instance)
        assert 'output "topic_arn"' in hcl
        assert "aws_sns_topic.alerts.arn" in hcl

    def test_outputs_contain_topic_name(self):
        """Outputs include topic_name referencing the SNS topic name."""
        instance = _sns_instance("alerts")
        hcl = self.gen.generate_outputs_tf(instance)
        assert 'output "topic_name"' in hcl
        assert "aws_sns_topic.alerts.name" in hcl


# ===========================================================================
# 5. SQSGenerator — generate_resource_tf
# ===========================================================================

class TestSQSGeneratorResourceTf:
    """Test SQSGenerator.generate_resource_tf produces valid aws_sqs_queue HCL."""

    def setup_method(self):
        self.gen = SQSGenerator()

    def test_minimal_sqs_queue(self):
        """A minimal SQS queue produces an aws_sqs_queue with only name."""
        instance = _sqs_instance("order-events")
        hcl = self.gen.generate_resource_tf(instance)
        assert 'resource "aws_sqs_queue" "order-events"' in hcl
        assert "name = var.queue_name" in hcl

    def test_sqs_with_visibility_timeout(self):
        """When visibility_timeout_seconds is set, the HCL includes it."""
        instance = _sqs_instance(visibility_timeout_seconds=60)
        hcl = self.gen.generate_resource_tf(instance)
        assert "visibility_timeout_seconds = var.visibility_timeout_seconds" in hcl

    def test_sqs_with_message_retention(self):
        """When message_retention_seconds is set, the HCL includes it."""
        instance = _sqs_instance(message_retention_seconds=86400)
        hcl = self.gen.generate_resource_tf(instance)
        assert "message_retention_seconds = var.message_retention_seconds" in hcl

    def test_sqs_with_delay_seconds(self):
        """When delay_seconds is set, the HCL includes it."""
        instance = _sqs_instance(delay_seconds=5)
        hcl = self.gen.generate_resource_tf(instance)
        assert "delay_seconds = var.delay_seconds" in hcl

    def test_sqs_with_max_message_size(self):
        """When max_message_size is set, the HCL includes it."""
        instance = _sqs_instance(max_message_size=262144)
        hcl = self.gen.generate_resource_tf(instance)
        assert "max_message_size = var.max_message_size" in hcl

    def test_sqs_with_tags(self):
        """When tags are set, the HCL includes tags attribute."""
        instance = _sqs_instance(tags={"team": "backend"})
        hcl = self.gen.generate_resource_tf(instance)
        assert "tags = var.tags" in hcl

    def test_sqs_without_optional_attrs_excludes_them(self):
        """When optional attributes are not set, they are absent from HCL."""
        instance = _sqs_instance()
        hcl = self.gen.generate_resource_tf(instance)
        assert "visibility_timeout_seconds" not in hcl
        assert "message_retention_seconds" not in hcl
        assert "fifo_queue" not in hcl
        assert "content_based_deduplication" not in hcl
        assert "delay_seconds" not in hcl
        assert "max_message_size" not in hcl
        assert "tags" not in hcl


# ===========================================================================
# 6. SQSGenerator — FIFO queue
# ===========================================================================

class TestSQSGeneratorFifo:
    """Test SQSGenerator with fifo_queue=True includes fifo and deduplication."""

    def setup_method(self):
        self.gen = SQSGenerator()

    def test_fifo_queue_includes_fifo_attribute(self):
        """When fifo_queue=True, the HCL includes fifo_queue."""
        instance = _sqs_instance(fifo_queue=True)
        hcl = self.gen.generate_resource_tf(instance)
        assert "fifo_queue = var.fifo_queue" in hcl

    def test_fifo_queue_with_deduplication(self):
        """When fifo_queue=True and content_based_deduplication=True, both appear."""
        instance = _sqs_instance(fifo_queue=True, content_based_deduplication=True)
        hcl = self.gen.generate_resource_tf(instance)
        assert "fifo_queue = var.fifo_queue" in hcl
        assert "content_based_deduplication = var.content_based_deduplication" in hcl


# ===========================================================================
# 7. SQSGenerator — generate_variables_tf
# ===========================================================================

class TestSQSGeneratorVariablesTf:
    """Test SQSGenerator.generate_variables_tf produces correct variable blocks."""

    def setup_method(self):
        self.gen = SQSGenerator()

    def test_minimal_variables(self):
        """A minimal SQS instance produces a queue_name variable."""
        instance = _sqs_instance()
        hcl = self.gen.generate_variables_tf(instance)
        assert 'variable "queue_name"' in hcl
        assert "type        = string" in hcl

    def test_variables_with_all_optional_fields(self):
        """When all optional fields are set, all corresponding variables appear."""
        instance = _sqs_instance(
            visibility_timeout_seconds=30,
            message_retention_seconds=345600,
            fifo_queue=True,
            content_based_deduplication=True,
            delay_seconds=0,
            max_message_size=262144,
            tags={"env": "staging"},
        )
        hcl = self.gen.generate_variables_tf(instance)
        assert 'variable "queue_name"' in hcl
        assert 'variable "visibility_timeout_seconds"' in hcl
        assert 'variable "message_retention_seconds"' in hcl
        assert 'variable "fifo_queue"' in hcl
        assert 'variable "content_based_deduplication"' in hcl
        assert 'variable "delay_seconds"' in hcl
        assert 'variable "max_message_size"' in hcl
        assert 'variable "tags"' in hcl

    def test_variables_include_defaults(self):
        """Variable blocks include default values from the config."""
        instance = _sqs_instance(visibility_timeout_seconds=45)
        hcl = self.gen.generate_variables_tf(instance)
        assert "default     = 45" in hcl


# ===========================================================================
# 8. SQSGenerator — generate_outputs_tf
# ===========================================================================

class TestSQSGeneratorOutputsTf:
    """Test SQSGenerator.generate_outputs_tf produces queue_arn and queue_url outputs."""

    def setup_method(self):
        self.gen = SQSGenerator()

    def test_outputs_contain_queue_arn(self):
        """Outputs include queue_arn referencing the SQS queue ARN."""
        instance = _sqs_instance("order-events")
        hcl = self.gen.generate_outputs_tf(instance)
        assert 'output "queue_arn"' in hcl
        assert "aws_sqs_queue.order-events.arn" in hcl

    def test_outputs_contain_queue_url(self):
        """Outputs include queue_url referencing the SQS queue URL."""
        instance = _sqs_instance("order-events")
        hcl = self.gen.generate_outputs_tf(instance)
        assert 'output "queue_url"' in hcl
        assert "aws_sqs_queue.order-events.url" in hcl


# ===========================================================================
# 9. Registry — both generators registered
# ===========================================================================

class TestGeneratorRegistry:
    """Test both SNS and SQS generators are registered in GENERATOR_REGISTRY."""

    def test_sns_generator_registered(self):
        """SNS generator is present in the registry."""
        assert ServiceType.SNS in GENERATOR_REGISTRY
        assert isinstance(GENERATOR_REGISTRY[ServiceType.SNS], SNSGenerator)

    def test_sqs_generator_registered(self):
        """SQS generator is present in the registry."""
        assert ServiceType.SQS in GENERATOR_REGISTRY
        assert isinstance(GENERATOR_REGISTRY[ServiceType.SQS], SQSGenerator)
