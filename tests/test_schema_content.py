"""Unit tests for VARIABLE_SCHEMAS content.

Verifies variable names, defaults, options, and group assignments per service
against the requirements (1.1–1.5, 2.1–2.5, 3.5–3.6, 5.3–5.11).
"""


from app.generators.variable_schemas import VARIABLE_SCHEMAS, VariableSchemaEntry
from app.models.input_models import ServiceType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _names(service: ServiceType) -> list[str]:
    """Return variable names for a service."""
    return [e.name for e in VARIABLE_SCHEMAS[service]]


def _entry(service: ServiceType, name: str) -> VariableSchemaEntry:
    """Look up a single schema entry by service + variable name."""
    for e in VARIABLE_SCHEMAS[service]:
        if e.name == name:
            return e
    raise KeyError(f"{service.value} has no variable '{name}'")


def _option_values(entry: VariableSchemaEntry) -> list:
    """Extract raw option values from an entry."""
    assert entry.options is not None, f"{entry.name} has no options"
    return [o.value for o in entry.options]


def _group_members(service: ServiceType, group: str) -> set[str]:
    """Return variable names belonging to a group."""
    return {e.name for e in VARIABLE_SCHEMAS[service] if e.group == group}


# ===================================================================
# 1. Variable names per service (Requirements 2.1–2.5)
# ===================================================================


class TestVariableNamesPerService:
    """Verify each service type has the expected variable names."""

    def test_lambda_variables(self):
        expected = {
            "function_name",
            "handler",
            "runtime",
            "memory_size",
            "timeout",
            "description",
            "environment_variables",
            "tags",
            "layers",
            "architectures",
            "ephemeral_storage_size",
            "reserved_concurrent_executions",
            "publish",
        }
        assert set(_names(ServiceType.LAMBDA)) == expected

    def test_s3_variables(self):
        expected = {
            "bucket_name",
            "versioning",
            "tags",
            "force_destroy",
            "object_lock_enabled",
            "acceleration_status",
        }
        assert set(_names(ServiceType.S3)) == expected

    def test_dynamodb_variables(self):
        expected = {
            "table_name",
            "billing_mode",
            "hash_key",
            "hash_key_type",
            "range_key",
            "range_key_type",
            "read_capacity",
            "write_capacity",
            "tags",
            "point_in_time_recovery_enabled",
            "deletion_protection_enabled",
            "table_class",
        }
        assert set(_names(ServiceType.DYNAMODB)) == expected

    def test_api_gateway_variables(self):
        expected = {
            # General
            "api_name",
            "protocol_type",
            "description",
            # Routes
            "route_method",
            "route_path",
            "route_selection_expression",
            # Stages
            "stage_name",
            "auto_deploy",
            "stage_variables",
            # Authorizers
            "authorizer_type",
            "jwt_issuer",
            "jwt_audience",
            "lambda_authorizer_uri",
            "authorizer_payload_format_version",
            "cognito_user_pool_endpoint",
            "cognito_client_ids",
            # Custom Domain
            "custom_domain_name",
            "certificate_arn",
            # Integrations
            "integration_type",
            "integration_uri",
            "integration_method",
            # Rate Limiting
            "throttling_burst_limit",
            "throttling_rate_limit",
            # VPC Link
            "vpc_link_name",
            "vpc_link_subnet_ids",
            "vpc_link_security_group_ids",
            # Metadata
            "cors_configuration",
            "disable_execute_api_endpoint",
            "api_key_required",
            "tags",
        }
        assert set(_names(ServiceType.API_GATEWAY)) == expected

    def test_cloudwatch_variables(self):
        expected = {
            "log_group_name",
            "retention_in_days",
            "tags",
            "kms_key_id",
            "log_group_class",
        }
        assert set(_names(ServiceType.CLOUDWATCH)) == expected


# ===================================================================
# 2. Specific defaults (Requirements 1.1–1.5)
# ===================================================================


class TestSpecificDefaults:
    """Verify well-known default values per service."""

    def test_lambda_handler_default(self):
        assert (
            _entry(ServiceType.LAMBDA, "handler").default
            == "lambda_function.lambda_handler"
        )

    def test_lambda_runtime_default(self):
        assert _entry(ServiceType.LAMBDA, "runtime").default == "python3.12"

    def test_lambda_memory_size_default(self):
        assert _entry(ServiceType.LAMBDA, "memory_size").default == 128

    def test_lambda_timeout_default(self):
        assert _entry(ServiceType.LAMBDA, "timeout").default == 3

    def test_s3_versioning_default(self):
        assert _entry(ServiceType.S3, "versioning").default == "Enabled"

    def test_dynamodb_billing_mode_default(self):
        assert _entry(ServiceType.DYNAMODB, "billing_mode").default == "PAY_PER_REQUEST"

    def test_dynamodb_hash_key_type_default(self):
        assert _entry(ServiceType.DYNAMODB, "hash_key_type").default == "S"

    def test_api_gateway_protocol_type_default(self):
        assert _entry(ServiceType.API_GATEWAY, "protocol_type").default == "HTTP"

    def test_cloudwatch_retention_in_days_default(self):
        assert _entry(ServiceType.CLOUDWATCH, "retention_in_days").default == 30


# ===================================================================
# 3. Specific options (Requirements 5.3–5.11)
# ===================================================================


class TestSpecificOptions:
    """Verify predefined option values for constrained fields."""

    def test_lambda_runtime_options(self):
        vals = _option_values(_entry(ServiceType.LAMBDA, "runtime"))
        for rt in ("python3.12", "nodejs20.x", "java21"):
            assert rt in vals

    def test_lambda_architectures_options(self):
        vals = _option_values(_entry(ServiceType.LAMBDA, "architectures"))
        assert set(vals) == {"x86_64", "arm64"}

    def test_dynamodb_billing_mode_options(self):
        vals = _option_values(_entry(ServiceType.DYNAMODB, "billing_mode"))
        assert set(vals) == {"PAY_PER_REQUEST", "PROVISIONED"}

    def test_dynamodb_hash_key_type_options(self):
        vals = _option_values(_entry(ServiceType.DYNAMODB, "hash_key_type"))
        assert set(vals) == {"S", "N", "B"}

    def test_api_gateway_protocol_type_options(self):
        vals = _option_values(_entry(ServiceType.API_GATEWAY, "protocol_type"))
        assert set(vals) == {"HTTP", "WEBSOCKET", "REST"}

    def test_cloudwatch_retention_in_days_options(self):
        vals = _option_values(_entry(ServiceType.CLOUDWATCH, "retention_in_days"))
        for v in (0, 1, 3, 5, 7, 14, 30):
            assert v in vals

    def test_cloudwatch_log_group_class_options(self):
        vals = _option_values(_entry(ServiceType.CLOUDWATCH, "log_group_class"))
        assert set(vals) == {"STANDARD", "INFREQUENT_ACCESS"}


# ===================================================================
# 4. Group assignments (Requirements 3.5–3.6)
# ===================================================================


class TestGroupAssignments:
    """Verify group organization for Lambda and DynamoDB."""

    # Lambda groups
    def test_lambda_general_group(self):
        assert _group_members(ServiceType.LAMBDA, "General") == {
            "function_name",
            "handler",
            "runtime",
            "description",
        }

    def test_lambda_performance_group(self):
        assert _group_members(ServiceType.LAMBDA, "Performance") == {
            "memory_size",
            "timeout",
            "ephemeral_storage_size",
            "reserved_concurrent_executions",
            "architectures",
        }

    def test_lambda_deployment_group(self):
        assert _group_members(ServiceType.LAMBDA, "Deployment") == {
            "publish",
            "layers",
        }

    def test_lambda_metadata_group(self):
        assert _group_members(ServiceType.LAMBDA, "Metadata") == {
            "environment_variables",
            "tags",
        }

    # DynamoDB groups
    def test_dynamodb_general_group(self):
        assert _group_members(ServiceType.DYNAMODB, "General") == {
            "table_name",
            "billing_mode",
            "table_class",
        }

    def test_dynamodb_key_schema_group(self):
        assert _group_members(ServiceType.DYNAMODB, "Key Schema") == {
            "hash_key",
            "hash_key_type",
            "range_key",
            "range_key_type",
        }

    def test_dynamodb_capacity_group(self):
        assert _group_members(ServiceType.DYNAMODB, "Capacity") == {
            "read_capacity",
            "write_capacity",
        }

    def test_dynamodb_metadata_group(self):
        assert _group_members(ServiceType.DYNAMODB, "Metadata") == {
            "tags",
            "point_in_time_recovery_enabled",
            "deletion_protection_enabled",
        }
