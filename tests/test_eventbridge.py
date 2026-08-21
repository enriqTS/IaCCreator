"""EventBridge rules and the targets they fire at."""

import pytest

from app.generators.eventbridge_generator import EventBridgeGenerator
from app.models.input_models import ServiceType
from app.models.input_models.eventbridge_config import EventBridgeConfig
from app.models.ir_models import ResourceInstanceIR
from app.services.connection_handlers.registry import CONNECTION_REGISTRY
from tests.reference_project import reference_tree

RULE_DIR = "reference-project/modules/messaging/eventbridge/nightly/"


def _instance(**config) -> ResourceInstanceIR:
    return ResourceInstanceIR(
        name="nightly",
        service_type=ServiceType.EVENTBRIDGE,
        config=EventBridgeConfig(**config),
    )


@pytest.fixture(scope="module")
def tree():
    return reference_tree()


class TestRuleGeneration:
    def test_schedule_and_state_are_emitted(self):
        hcl = EventBridgeGenerator().generate_resource_tf(
            _instance(
                rule_name="nightly", schedule_expression="rate(1 day)", state="ENABLED"
            )
        )
        assert 'resource "aws_cloudwatch_event_rule" "nightly"' in hcl
        assert "schedule_expression = var.schedule_expression" in hcl
        assert "state = var.state" in hcl

    def test_event_pattern_is_emitted(self):
        hcl = EventBridgeGenerator().generate_resource_tf(
            _instance(rule_name="on-change", event_pattern='{"source":["aws.s3"]}')
        )
        assert "event_pattern = var.event_pattern" in hcl

    def test_a_custom_bus_is_created_and_referenced(self):
        hcl = EventBridgeGenerator().generate_resource_tf(
            _instance(rule_name="nightly", bus_name="ops")
        )
        assert 'resource "aws_cloudwatch_event_bus" "nightly_bus"' in hcl
        assert "event_bus_name = aws_cloudwatch_event_bus.nightly_bus.name" in hcl

    def test_the_default_bus_is_left_implicit(self):
        hcl = EventBridgeGenerator().generate_resource_tf(
            _instance(rule_name="nightly")
        )
        assert "aws_cloudwatch_event_bus" not in hcl

    def test_rule_name_defaults_to_the_instance_name(self):
        variables = EventBridgeGenerator().generate_variables_tf(_instance())
        assert 'default     = "nightly"' in variables

    def test_outputs_expose_the_rule(self):
        outputs = EventBridgeGenerator().generate_outputs_tf(
            _instance(rule_name="nightly")
        )
        assert 'output "rule_arn"' in outputs
        assert 'output "rule_name"' in outputs


class TestTargetsAreOwnedByTheRule:
    """Values flow target → rule only, so Terraform sees no dependency cycle."""

    def test_lambda_target_and_permission_live_with_the_rule(self, tree):
        files = {p.rsplit("/", 1)[-1] for p in tree if RULE_DIR in p}
        assert {"target_process-job.tf", "permission_process-job.tf"} <= files

    def test_queue_target_and_policy_live_with_the_rule(self, tree):
        files = {p.rsplit("/", 1)[-1] for p in tree if RULE_DIR in p}
        assert {"target_audit.tf", "policy_audit.tf"} <= files

    def test_target_reads_the_arn_as_an_input(self, tree):
        assert (
            "arn = var.process_job_function_arn"
            in tree[RULE_DIR + "target_process-job.tf"]
        )

    def test_configured_target_id_is_used(self, tree):
        assert (
            'target_id = "nightly-processor"'
            in tree[RULE_DIR + "target_process-job.tf"]
        )

    def test_target_id_defaults_to_the_target_name(self, tree):
        assert 'target_id = "audit"' in tree[RULE_DIR + "target_audit.tf"]

    def test_permission_is_scoped_to_the_rule(self, tree):
        content = tree[RULE_DIR + "permission_process-job.tf"]
        assert 'principal = "events.amazonaws.com"' in content
        assert "source_arn = aws_cloudwatch_event_rule.nightly.arn" in content

    def test_one_rule_wires_targets_of_different_services(self, tree):
        main = tree["reference-project/environments/dev/main.tf"]
        block = main[main.index('module "nightly"') :]
        block = block[: block.index("}")]
        assert "process_job_function_arn = module.process-job.function_arn" in block
        assert "audit_queue_arn = module.audit.arn" in block


class TestRegistration:
    @pytest.mark.parametrize("target", [ServiceType.LAMBDA, ServiceType.SQS])
    def test_targets_are_registered(self, target):
        assert (ServiceType.EVENTBRIDGE, target, "targets") in CONNECTION_REGISTRY

    def test_the_service_generates_into_messaging(self, tree):
        assert any("/modules/messaging/eventbridge/" in p for p in tree)
