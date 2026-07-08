"""S3 service generator — produces HCL for aws_s3_bucket resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.s3_config import S3Config
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> S3Config:
    """Resolve typed S3Config from instance config.

    Falls back to duck-typed access if field names match.
    """
    if isinstance(instance.config, S3Config):
        return instance.config
    # Fallback: duck-typed access works if field names match
    return instance.config  # type: ignore[return-value]


class S3Generator:
    """Generates Terraform files for S3 buckets."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    # ── Companion resource helpers ───────────────────────────────────────────

    def _generate_encryption_config(
        self, instance: ResourceInstanceIR, config: S3Config
    ) -> str:
        """Emit aws_s3_bucket_server_side_encryption_configuration when encryption fields are set."""
        if config.sse_algorithm is None:
            return ""

        apply_default: dict = {
            "sse_algorithm": "var.sse_algorithm",
        }
        if config.sse_kms_key_id is not None:
            apply_default["kms_master_key_id"] = "var.sse_kms_key_id"

        rule: dict = {
            "apply_server_side_encryption_by_default": apply_default,
        }
        if config.sse_bucket_key_enabled is not None:
            rule["bucket_key_enabled"] = "var.sse_bucket_key_enabled"

        attrs = {
            "bucket": f"aws_s3_bucket.{instance.name}.id",
            "rule": rule,
        }

        return "\n" + self._r.render_resource(
            "aws_s3_bucket_server_side_encryption_configuration",
            f"{instance.name}_encryption",
            attrs,
        )

    def _generate_cors_config(
        self, instance: ResourceInstanceIR, config: S3Config
    ) -> str:
        """Emit aws_s3_bucket_cors_configuration when CORS fields are set."""
        has_cors = any(
            [
                config.cors_allowed_headers is not None,
                config.cors_allowed_methods is not None,
                config.cors_allowed_origins is not None,
                config.cors_expose_headers is not None,
                config.cors_max_age_seconds is not None,
            ]
        )
        if not has_cors:
            return ""

        cors_rule: dict = {}
        if config.cors_allowed_headers is not None:
            cors_rule["allowed_headers"] = "var.cors_allowed_headers"
        if config.cors_allowed_methods is not None:
            cors_rule["allowed_methods"] = "var.cors_allowed_methods"
        if config.cors_allowed_origins is not None:
            cors_rule["allowed_origins"] = "var.cors_allowed_origins"
        if config.cors_expose_headers is not None:
            cors_rule["expose_headers"] = "var.cors_expose_headers"
        if config.cors_max_age_seconds is not None:
            cors_rule["max_age_seconds"] = "var.cors_max_age_seconds"

        attrs = {
            "bucket": f"aws_s3_bucket.{instance.name}.id",
            "cors_rule": cors_rule,
        }

        return "\n" + self._r.render_resource(
            "aws_s3_bucket_cors_configuration",
            f"{instance.name}_cors",
            attrs,
        )

    def _generate_logging_config(
        self, instance: ResourceInstanceIR, config: S3Config
    ) -> str:
        """Emit aws_s3_bucket_logging when logging fields are set."""
        if config.logging_target_bucket is None:
            return ""

        attrs: dict = {
            "bucket": f"aws_s3_bucket.{instance.name}.id",
            "target_bucket": "var.logging_target_bucket",
        }
        if config.logging_target_prefix is not None:
            attrs["target_prefix"] = "var.logging_target_prefix"

        return "\n" + self._r.render_resource(
            "aws_s3_bucket_logging",
            f"{instance.name}_logging",
            attrs,
        )

    def _generate_website_config(
        self, instance: ResourceInstanceIR, config: S3Config
    ) -> str:
        """Emit aws_s3_bucket_website_configuration when website fields are set."""
        has_website = any(
            [
                config.website_index_document is not None,
                config.website_error_document is not None,
                config.website_redirect_all_requests_to is not None,
            ]
        )
        if not has_website:
            return ""

        attrs: dict = {
            "bucket": f"aws_s3_bucket.{instance.name}.id",
        }

        if config.website_redirect_all_requests_to is not None:
            attrs["redirect_all_requests_to"] = {
                "host_name": "var.website_redirect_all_requests_to",
            }
        else:
            if config.website_index_document is not None:
                attrs["index_document"] = {
                    "suffix": "var.website_index_document",
                }
            if config.website_error_document is not None:
                attrs["error_document"] = {
                    "key": "var.website_error_document",
                }

        return "\n" + self._r.render_resource(
            "aws_s3_bucket_website_configuration",
            f"{instance.name}_website",
            attrs,
        )

    def _generate_public_access_block(
        self, instance: ResourceInstanceIR, config: S3Config
    ) -> str:
        """Emit aws_s3_bucket_public_access_block when public access fields differ from defaults."""
        # Emit when at least one field is non-None and differs from True (the default)
        has_non_default = any(
            [
                config.block_public_acls is not None
                and config.block_public_acls is not True,
                config.block_public_policy is not None
                and config.block_public_policy is not True,
                config.ignore_public_acls is not None
                and config.ignore_public_acls is not True,
                config.restrict_public_buckets is not None
                and config.restrict_public_buckets is not True,
            ]
        )
        if not has_non_default:
            return ""

        attrs: dict = {
            "bucket": f"aws_s3_bucket.{instance.name}.id",
        }
        if config.block_public_acls is not None:
            attrs["block_public_acls"] = "var.block_public_acls"
        if config.block_public_policy is not None:
            attrs["block_public_policy"] = "var.block_public_policy"
        if config.ignore_public_acls is not None:
            attrs["ignore_public_acls"] = "var.ignore_public_acls"
        if config.restrict_public_buckets is not None:
            attrs["restrict_public_buckets"] = "var.restrict_public_buckets"

        return "\n" + self._r.render_resource(
            "aws_s3_bucket_public_access_block",
            f"{instance.name}_public_access_block",
            attrs,
        )

    def _generate_notification_config(
        self, instance: ResourceInstanceIR, config: S3Config
    ) -> str:
        """Emit aws_s3_bucket_notification when notification fields are set."""
        has_notifications = any(
            [
                config.notification_lambda_arn is not None,
                config.notification_sqs_arn is not None,
                config.notification_sns_arn is not None,
            ]
        )
        if not has_notifications:
            return ""

        attrs: dict = {
            "bucket": f"aws_s3_bucket.{instance.name}.id",
        }

        if config.notification_lambda_arn is not None:
            lambda_block: dict = {
                "lambda_function_arn": "var.notification_lambda_arn",
            }
            if config.notification_lambda_events is not None:
                lambda_block["events"] = "var.notification_lambda_events"
            attrs["lambda_function"] = lambda_block

        if config.notification_sqs_arn is not None:
            queue_block: dict = {
                "queue_arn": "var.notification_sqs_arn",
            }
            if config.notification_sqs_events is not None:
                queue_block["events"] = "var.notification_sqs_events"
            attrs["queue"] = queue_block

        if config.notification_sns_arn is not None:
            topic_block: dict = {
                "topic_arn": "var.notification_sns_arn",
            }
            if config.notification_sns_events is not None:
                topic_block["events"] = "var.notification_sns_events"
            attrs["topic"] = topic_block

        return "\n" + self._r.render_resource(
            "aws_s3_bucket_notification",
            f"{instance.name}_notification",
            attrs,
        )

    def _generate_replication_config(
        self, instance: ResourceInstanceIR, config: S3Config
    ) -> str:
        """Emit aws_s3_bucket_replication_configuration when replication fields are set."""
        if config.replication_role_arn is None:
            return ""

        destination: dict = {}
        if config.replication_destination_bucket is not None:
            destination["bucket"] = "var.replication_destination_bucket"
        if config.replication_destination_storage_class is not None:
            destination["storage_class"] = "var.replication_destination_storage_class"

        attrs: dict = {
            "bucket": f"aws_s3_bucket.{instance.name}.id",
            "role": "var.replication_role_arn",
            "rule": {
                "status": '"Enabled"',
                "destination": destination,
            },
        }

        return "\n" + self._r.render_resource(
            "aws_s3_bucket_replication_configuration",
            f"{instance.name}_replication",
            attrs,
        )

    # ── Main generation methods ──────────────────────────────────────────────

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate s3.tf with aws_s3_bucket resource and companion resources."""
        config = _resolve_config(instance)

        attrs: dict = {"bucket": "var.bucket_name"}
        if config.force_destroy is not None:
            attrs["force_destroy"] = "var.force_destroy"
        if config.object_lock_enabled is not None:
            attrs["object_lock_enabled"] = "var.object_lock_enabled"
        if config.tags is not None:
            attrs["tags"] = "var.tags"

        result = self._r.render_resource("aws_s3_bucket", instance.name, attrs)

        versioning_attrs = {
            "bucket": f"aws_s3_bucket.{instance.name}.id",
            "versioning_configuration": {"status": "var.versioning_enabled"},
        }
        result += "\n" + self._r.render_resource(
            "aws_s3_bucket_versioning", f"{instance.name}_versioning", versioning_attrs
        )

        if config.acceleration_status is not None:
            accel_attrs = {
                "bucket": f"aws_s3_bucket.{instance.name}.id",
                "status": "var.acceleration_status",
            }
            result += "\n" + self._r.render_resource(
                "aws_s3_bucket_accelerate_configuration",
                f"{instance.name}_accelerate",
                accel_attrs,
            )

        # Companion resources
        result += self._generate_encryption_config(instance, config)
        result += self._generate_cors_config(instance, config)
        result += self._generate_logging_config(instance, config)
        result += self._generate_website_config(instance, config)
        result += self._generate_public_access_block(instance, config)
        result += self._generate_notification_config(instance, config)
        result += self._generate_replication_config(instance, config)

        return result

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an S3 instance."""
        config = _resolve_config(instance)

        parts = [
            self._r.render_variable("bucket_name", "string", "Name of the S3 bucket"),
            self._r.render_variable(
                "versioning_enabled",
                "string",
                "Versioning status (Enabled or Suspended)",
                default="Enabled",
            ),
        ]
        if config.force_destroy is not None:
            parts.append(
                self._r.render_variable(
                    "force_destroy",
                    "bool",
                    "Allow deletion of non-empty bucket by deleting all objects",
                    default=config.force_destroy,
                )
            )
        if config.object_lock_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "object_lock_enabled",
                    "bool",
                    "Enable S3 Object Lock on the bucket",
                    default=config.object_lock_enabled,
                )
            )
        if config.acceleration_status is not None:
            parts.append(
                self._r.render_variable(
                    "acceleration_status",
                    "string",
                    "Transfer acceleration status for the bucket",
                    default=config.acceleration_status,
                )
            )
        if config.tags is not None:
            parts.append(
                self._r.render_variable(
                    "tags",
                    "map(string)",
                    "Tags to apply to the S3 bucket",
                )
            )

        # ── Encryption variables ─────────────────────────────────────────────
        if config.sse_algorithm is not None:
            parts.append(
                self._r.render_variable(
                    "sse_algorithm",
                    "string",
                    "Server-side encryption algorithm to use",
                    default=config.sse_algorithm,
                )
            )
        if config.sse_kms_key_id is not None:
            parts.append(
                self._r.render_variable(
                    "sse_kms_key_id",
                    "string",
                    "ARN of the KMS key to use for server-side encryption",
                    default=config.sse_kms_key_id,
                )
            )
        if config.sse_bucket_key_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "sse_bucket_key_enabled",
                    "bool",
                    "Whether to enable S3 Bucket Key for SSE-KMS",
                    default=config.sse_bucket_key_enabled,
                )
            )

        # ── CORS variables ───────────────────────────────────────────────────
        if config.cors_allowed_headers is not None:
            parts.append(
                self._r.render_variable(
                    "cors_allowed_headers",
                    "list(string)",
                    "List of headers allowed in CORS requests",
                    default=config.cors_allowed_headers,
                )
            )
        if config.cors_allowed_methods is not None:
            parts.append(
                self._r.render_variable(
                    "cors_allowed_methods",
                    "list(string)",
                    "List of HTTP methods allowed in CORS requests",
                    default=config.cors_allowed_methods,
                )
            )
        if config.cors_allowed_origins is not None:
            parts.append(
                self._r.render_variable(
                    "cors_allowed_origins",
                    "list(string)",
                    "List of origins allowed to make CORS requests",
                    default=config.cors_allowed_origins,
                )
            )
        if config.cors_expose_headers is not None:
            parts.append(
                self._r.render_variable(
                    "cors_expose_headers",
                    "list(string)",
                    "List of headers exposed to the browser in CORS responses",
                    default=config.cors_expose_headers,
                )
            )
        if config.cors_max_age_seconds is not None:
            parts.append(
                self._r.render_variable(
                    "cors_max_age_seconds",
                    "number",
                    "Time in seconds the browser can cache the preflight response",
                    default=config.cors_max_age_seconds,
                )
            )

        # ── Logging variables ────────────────────────────────────────────────
        if config.logging_target_bucket is not None:
            parts.append(
                self._r.render_variable(
                    "logging_target_bucket",
                    "string",
                    "Name of the bucket to receive access logs",
                    default=config.logging_target_bucket,
                )
            )
        if config.logging_target_prefix is not None:
            parts.append(
                self._r.render_variable(
                    "logging_target_prefix",
                    "string",
                    "Prefix for access log object keys",
                    default=config.logging_target_prefix,
                )
            )

        # ── Website variables ────────────────────────────────────────────────
        if config.website_index_document is not None:
            parts.append(
                self._r.render_variable(
                    "website_index_document",
                    "string",
                    "Name of the index document for the website",
                    default=config.website_index_document,
                )
            )
        if config.website_error_document is not None:
            parts.append(
                self._r.render_variable(
                    "website_error_document",
                    "string",
                    "Name of the error document for the website",
                    default=config.website_error_document,
                )
            )
        if config.website_redirect_all_requests_to is not None:
            parts.append(
                self._r.render_variable(
                    "website_redirect_all_requests_to",
                    "string",
                    "Hostname to redirect all website requests to",
                    default=config.website_redirect_all_requests_to,
                )
            )

        # ── Public Access variables ──────────────────────────────────────────
        if config.block_public_acls is not None:
            parts.append(
                self._r.render_variable(
                    "block_public_acls",
                    "bool",
                    "Whether to block public ACLs for the bucket",
                    default=config.block_public_acls,
                )
            )
        if config.block_public_policy is not None:
            parts.append(
                self._r.render_variable(
                    "block_public_policy",
                    "bool",
                    "Whether to block public bucket policies",
                    default=config.block_public_policy,
                )
            )
        if config.ignore_public_acls is not None:
            parts.append(
                self._r.render_variable(
                    "ignore_public_acls",
                    "bool",
                    "Whether to ignore public ACLs for the bucket",
                    default=config.ignore_public_acls,
                )
            )
        if config.restrict_public_buckets is not None:
            parts.append(
                self._r.render_variable(
                    "restrict_public_buckets",
                    "bool",
                    "Whether to restrict public bucket policies",
                    default=config.restrict_public_buckets,
                )
            )

        # ── Notification variables ───────────────────────────────────────────
        if config.notification_lambda_arn is not None:
            parts.append(
                self._r.render_variable(
                    "notification_lambda_arn",
                    "string",
                    "ARN of the Lambda function for bucket notifications",
                    default=config.notification_lambda_arn,
                )
            )
        if config.notification_lambda_events is not None:
            parts.append(
                self._r.render_variable(
                    "notification_lambda_events",
                    "list(string)",
                    "S3 events that trigger the Lambda notification",
                    default=config.notification_lambda_events,
                )
            )
        if config.notification_sqs_arn is not None:
            parts.append(
                self._r.render_variable(
                    "notification_sqs_arn",
                    "string",
                    "ARN of the SQS queue for bucket notifications",
                    default=config.notification_sqs_arn,
                )
            )
        if config.notification_sqs_events is not None:
            parts.append(
                self._r.render_variable(
                    "notification_sqs_events",
                    "list(string)",
                    "S3 events that trigger the SQS notification",
                    default=config.notification_sqs_events,
                )
            )
        if config.notification_sns_arn is not None:
            parts.append(
                self._r.render_variable(
                    "notification_sns_arn",
                    "string",
                    "ARN of the SNS topic for bucket notifications",
                    default=config.notification_sns_arn,
                )
            )
        if config.notification_sns_events is not None:
            parts.append(
                self._r.render_variable(
                    "notification_sns_events",
                    "list(string)",
                    "S3 events that trigger the SNS notification",
                    default=config.notification_sns_events,
                )
            )

        # ── Replication variables ────────────────────────────────────────────
        if config.replication_role_arn is not None:
            parts.append(
                self._r.render_variable(
                    "replication_role_arn",
                    "string",
                    "ARN of the IAM role for S3 replication",
                    default=config.replication_role_arn,
                )
            )
        if config.replication_destination_bucket is not None:
            parts.append(
                self._r.render_variable(
                    "replication_destination_bucket",
                    "string",
                    "ARN of the destination bucket for replication",
                    default=config.replication_destination_bucket,
                )
            )
        if config.replication_destination_storage_class is not None:
            parts.append(
                self._r.render_variable(
                    "replication_destination_storage_class",
                    "string",
                    "Storage class for replicated objects in the destination bucket",
                    default=config.replication_destination_storage_class,
                )
            )

        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an S3 instance."""
        parts = [
            self._r.render_output(
                "bucket_arn",
                f"aws_s3_bucket.{instance.name}.arn",
                "ARN of the S3 bucket",
            ),
            self._r.render_output(
                "bucket_name",
                f"aws_s3_bucket.{instance.name}.id",
                "Name of the S3 bucket",
            ),
        ]
        return "\n".join(parts)
