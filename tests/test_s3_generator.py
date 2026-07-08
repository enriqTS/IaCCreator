"""Unit tests for S3 generator companion resources.

Validates Requirements: 2.11, 2.12, 2.13, 2.14, 2.15, 2.16, 2.17
"""

import pytest

from app.generators.s3_generator import S3Generator
from app.models.input_models._general import ServiceType
from app.models.input_models.s3_config import S3Config
from app.models.ir_models import ResourceInstanceIR


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_instance(config: S3Config, name: str = "test_bucket") -> ResourceInstanceIR:
    """Create a ResourceInstanceIR with S3Config for testing."""
    return ResourceInstanceIR(name=name, service_type=ServiceType.S3, config=config)


def _generate(config: S3Config, name: str = "test_bucket") -> str:
    """Generate resource TF output for a given S3Config."""
    instance = _make_instance(config, name)
    gen = S3Generator()
    return gen.generate_resource_tf(instance)


# ── Encryption companion (Requirement 2.11) ─────────────────────────────────


class TestEncryptionCompanion:
    """Tests for aws_s3_bucket_server_side_encryption_configuration emission."""

    def test_encryption_emitted_when_sse_algorithm_set(self):
        config = S3Config(sse_algorithm="AES256")
        output = _generate(config)
        assert "aws_s3_bucket_server_side_encryption_configuration" in output

    def test_encryption_emitted_with_kms(self):
        config = S3Config(
            sse_algorithm="aws:kms",
            sse_kms_key_id="arn:aws:kms:us-east-1:123456789:key/abc",
        )
        output = _generate(config)
        assert "aws_s3_bucket_server_side_encryption_configuration" in output
        assert "kms_master_key_id" in output

    def test_encryption_emitted_with_bucket_key_enabled(self):
        config = S3Config(sse_algorithm="aws:kms", sse_bucket_key_enabled=True)
        output = _generate(config)
        assert "aws_s3_bucket_server_side_encryption_configuration" in output
        assert "bucket_key_enabled" in output

    def test_encryption_not_emitted_when_sse_algorithm_none(self):
        config = S3Config()
        output = _generate(config)
        assert "aws_s3_bucket_server_side_encryption_configuration" not in output


# ── CORS companion (Requirement 2.12) ───────────────────────────────────────


class TestCorsCompanion:
    """Tests for aws_s3_bucket_cors_configuration emission."""

    def test_cors_emitted_when_cors_fields_set(self):
        config = S3Config(
            cors_allowed_methods=["GET", "POST"],
            cors_allowed_origins=["https://example.com"],
        )
        output = _generate(config)
        assert "aws_s3_bucket_cors_configuration" in output

    def test_cors_emitted_with_all_fields(self):
        config = S3Config(
            cors_allowed_headers=["*"],
            cors_allowed_methods=["GET"],
            cors_allowed_origins=["*"],
            cors_expose_headers=["ETag"],
            cors_max_age_seconds=3600,
        )
        output = _generate(config)
        assert "aws_s3_bucket_cors_configuration" in output

    def test_cors_not_emitted_when_fields_none(self):
        config = S3Config()
        output = _generate(config)
        assert "aws_s3_bucket_cors_configuration" not in output


# ── Logging companion (Requirement 2.13) ────────────────────────────────────


class TestLoggingCompanion:
    """Tests for aws_s3_bucket_logging emission."""

    def test_logging_emitted_when_target_bucket_set(self):
        config = S3Config(logging_target_bucket="my-logs-bucket")
        output = _generate(config)
        assert "aws_s3_bucket_logging" in output

    def test_logging_emitted_with_prefix(self):
        config = S3Config(
            logging_target_bucket="my-logs-bucket",
            logging_target_prefix="logs/",
        )
        output = _generate(config)
        assert "aws_s3_bucket_logging" in output
        assert "target_prefix" in output

    def test_logging_not_emitted_when_target_bucket_none(self):
        config = S3Config()
        output = _generate(config)
        assert "aws_s3_bucket_logging" not in output


# ── Website companion (Requirement 2.14) ────────────────────────────────────


class TestWebsiteCompanion:
    """Tests for aws_s3_bucket_website_configuration emission."""

    def test_website_emitted_when_index_document_set(self):
        config = S3Config(website_index_document="index.html")
        output = _generate(config)
        assert "aws_s3_bucket_website_configuration" in output

    def test_website_emitted_when_error_document_set(self):
        config = S3Config(website_error_document="error.html")
        output = _generate(config)
        assert "aws_s3_bucket_website_configuration" in output

    def test_website_emitted_when_redirect_set(self):
        config = S3Config(
            website_redirect_all_requests_to="https://example.com",
        )
        output = _generate(config)
        assert "aws_s3_bucket_website_configuration" in output
        assert "redirect_all_requests_to" in output

    def test_website_not_emitted_when_fields_none(self):
        config = S3Config()
        output = _generate(config)
        assert "aws_s3_bucket_website_configuration" not in output


# ── Public Access Block companion (Requirement 2.15) ─────────────────────────


class TestPublicAccessBlockCompanion:
    """Tests for aws_s3_bucket_public_access_block emission."""

    def test_public_access_block_emitted_when_value_differs_from_default(self):
        config = S3Config(block_public_acls=False)
        output = _generate(config)
        assert "aws_s3_bucket_public_access_block" in output

    def test_public_access_block_emitted_when_multiple_differ(self):
        config = S3Config(
            block_public_acls=False,
            block_public_policy=False,
            ignore_public_acls=False,
            restrict_public_buckets=False,
        )
        output = _generate(config)
        assert "aws_s3_bucket_public_access_block" in output

    def test_public_access_block_not_emitted_when_all_defaults(self):
        """All fields True (default) means no companion resource emitted."""
        config = S3Config(
            block_public_acls=True,
            block_public_policy=True,
            ignore_public_acls=True,
            restrict_public_buckets=True,
        )
        output = _generate(config)
        assert "aws_s3_bucket_public_access_block" not in output

    def test_public_access_block_not_emitted_for_default_config(self):
        """Default S3Config (no explicit public access fields) should not emit."""
        config = S3Config()
        output = _generate(config)
        assert "aws_s3_bucket_public_access_block" not in output


# ── Notification companion (Requirement 2.16) ───────────────────────────────


class TestNotificationCompanion:
    """Tests for aws_s3_bucket_notification emission."""

    def test_notification_emitted_when_lambda_arn_set(self):
        config = S3Config(
            notification_lambda_arn="arn:aws:lambda:us-east-1:123:function:my-func",
            notification_lambda_events=["s3:ObjectCreated:*"],
        )
        output = _generate(config)
        assert "aws_s3_bucket_notification" in output

    def test_notification_emitted_when_sqs_arn_set(self):
        config = S3Config(
            notification_sqs_arn="arn:aws:sqs:us-east-1:123:my-queue",
            notification_sqs_events=["s3:ObjectCreated:*"],
        )
        output = _generate(config)
        assert "aws_s3_bucket_notification" in output

    def test_notification_emitted_when_sns_arn_set(self):
        config = S3Config(
            notification_sns_arn="arn:aws:sns:us-east-1:123:my-topic",
            notification_sns_events=["s3:ObjectRemoved:*"],
        )
        output = _generate(config)
        assert "aws_s3_bucket_notification" in output

    def test_notification_not_emitted_when_fields_none(self):
        config = S3Config()
        output = _generate(config)
        assert "aws_s3_bucket_notification" not in output


# ── Replication companion (Requirement 2.17) ────────────────────────────────


class TestReplicationCompanion:
    """Tests for aws_s3_bucket_replication_configuration emission."""

    def test_replication_emitted_when_role_arn_set(self):
        config = S3Config(
            replication_role_arn="arn:aws:iam::123:role/repl-role",
            replication_destination_bucket="arn:aws:s3:::dest-bucket",
        )
        output = _generate(config)
        assert "aws_s3_bucket_replication_configuration" in output

    def test_replication_emitted_with_storage_class(self):
        config = S3Config(
            replication_role_arn="arn:aws:iam::123:role/repl-role",
            replication_destination_bucket="arn:aws:s3:::dest-bucket",
            replication_destination_storage_class="GLACIER",
        )
        output = _generate(config)
        assert "aws_s3_bucket_replication_configuration" in output
        assert "storage_class" in output

    def test_replication_not_emitted_when_fields_none(self):
        config = S3Config()
        output = _generate(config)
        assert "aws_s3_bucket_replication_configuration" not in output
