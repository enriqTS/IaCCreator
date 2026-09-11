"""Bucket notifications aggregate without losing external destinations."""

from itertools import permutations

from app.models.input_models import ArchitectureDescription
from app.services.code_generator import CodeGenerator
from app.services.ir_builder import IRBuilder
from tests.reference_project import reference_architecture


def test_multiple_lambda_notifications_are_deterministic_and_preserve_external():
    architecture = reference_architecture()
    bucket = next(item for item in architecture.resources if item.name == "uploads")
    bucket.config.notification_sqs_arn = "arn:aws:sqs:us-east-1:123456789012:external"
    original = next(
        item for item in architecture.connections if item.source == "uploads"
    )
    second = original.model_copy(
        update={
            "target": "on-change",
            "target_id": None,
            "connection_config": {"filter_suffix": ".json"},
        }
    )
    others = [item for item in architecture.connections if item is not original]
    results = []
    for connections in permutations([original, second, original]):
        candidate = ArchitectureDescription.model_validate(architecture.model_dump())
        candidate.connections = [*others, *connections]
        tree = CodeGenerator().generate(IRBuilder().build(candidate))
        content = tree["reference-project/modules/storage/s3/uploads/notifications.tf"]
        assert content.count("lambda_function {") == 2
        assert "var.notification_sqs_arn" in content
        assert "aws_lambda_permission.on_change_permission" in content
        assert (
            sum(
                text.count('resource "aws_s3_bucket_notification"')
                for text in tree.values()
            )
            == 1
        )
        results.append(tree)
    assert all(tree == results[0] for tree in results)
