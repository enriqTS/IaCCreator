"""Unit tests for Terraform IaC Generator."""

import pytest
from pydantic import ValidationError

from app.models.input_models import (
    ArchitectureDescription,
    ServiceType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_env(name: str = "dev") -> dict:
    return {"name": name, "variables": {"region": "us-east-1"}}


def _make_resource(name: str, service_type: str, **config_overrides) -> dict:
    config = {}
    if service_type == "lambda":
        config = {"function_name": name, "handler": "index.handler", "runtime": "python3.12"}
    elif service_type == "dynamodb":
        config = {"table_name": name, "hash_key": "id", "hash_key_type": "S", "billing_mode": "PAY_PER_REQUEST"}
    elif service_type == "api-gateway":
        config = {"api_name": name, "protocol_type": "HTTP"}
    elif service_type == "cloudwatch":
        config = {"retention_in_days": 14}
    config.update(config_overrides)
    return {"name": name, "service_type": service_type, "config": config}


def _valid_payload_all_services() -> dict:
    """Return a valid payload containing all six service types."""
    return {
        "project_name": "my-infra",
        "environments": [_make_env("dev"), _make_env("prod")],
        "resources": [
            _make_resource("my-func", "lambda"),
            _make_resource("my-bucket", "s3"),
            _make_resource("my-api", "api-gateway"),
            _make_resource("my-table", "dynamodb"),
            _make_resource("my-role", "iam"),
            _make_resource("my-logs", "cloudwatch"),
        ],
        "connections": [],
    }


# ---------------------------------------------------------------------------
# 1. Valid payload with all six service types passes validation
# ---------------------------------------------------------------------------


class TestValidPayloads:
    def test_valid_payload_all_six_service_types(self):
        """A valid payload containing all six service types passes validation."""
        payload = _valid_payload_all_services()
        desc = ArchitectureDescription(**payload)

        assert desc.project_name == "my-infra"
        assert len(desc.environments) == 2
        assert len(desc.resources) == 6
        service_types = {r.service_type for r in desc.resources}
        assert service_types == {
            ServiceType.LAMBDA,
            ServiceType.S3,
            ServiceType.API_GATEWAY,
            ServiceType.DYNAMODB,
            ServiceType.IAM,
            ServiceType.CLOUDWATCH,
        }

    @pytest.mark.parametrize(
        "service_type",
        ["lambda", "s3", "api-gateway", "dynamodb", "iam", "cloudwatch"],
    )
    def test_valid_payload_individual_service_type(self, service_type: str):
        """Valid payloads for each individual service type pass validation."""
        payload = {
            "project_name": "single-svc",
            "environments": [_make_env()],
            "resources": [_make_resource(f"res-{service_type}", service_type)],
        }
        desc = ArchitectureDescription(**payload)
        assert len(desc.resources) == 1
        assert desc.resources[0].service_type.value == service_type


# ---------------------------------------------------------------------------
# 2-4. Missing required fields return validation errors
# ---------------------------------------------------------------------------


class TestMissingRequiredFields:
    def test_missing_project_name(self):
        """Missing project_name raises ValidationError."""
        payload = _valid_payload_all_services()
        del payload["project_name"]
        with pytest.raises(ValidationError) as exc_info:
            ArchitectureDescription(**payload)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("project_name",) for e in errors)

    def test_empty_environments_list(self):
        """Empty environments list raises ValidationError (min_length=1)."""
        payload = _valid_payload_all_services()
        payload["environments"] = []
        with pytest.raises(ValidationError) as exc_info:
            ArchitectureDescription(**payload)
        errors = exc_info.value.errors()
        assert any("environments" in str(e["loc"]) for e in errors)

    def test_empty_resources_list(self):
        """Empty resources list raises ValidationError (min_length=1)."""
        payload = _valid_payload_all_services()
        payload["resources"] = []
        with pytest.raises(ValidationError) as exc_info:
            ArchitectureDescription(**payload)
        errors = exc_info.value.errors()
        assert any("resources" in str(e["loc"]) for e in errors)


# ---------------------------------------------------------------------------
# 5. Unsupported service type rejection
# ---------------------------------------------------------------------------


class TestUnsupportedServiceType:
    def test_unsupported_service_type_rejected(self):
        """An unsupported service_type string raises ValidationError."""
        payload = {
            "project_name": "bad-svc",
            "environments": [_make_env()],
            "resources": [
                {"name": "res", "service_type": "nonexistent-service", "config": {}},
            ],
        }
        with pytest.raises(ValidationError) as exc_info:
            ArchitectureDescription(**payload)
        errors = exc_info.value.errors()
        assert any("service_type" in str(e["loc"]) for e in errors)


# ---------------------------------------------------------------------------
# 6-7. DynamoDB custom validator
# ---------------------------------------------------------------------------


class TestDynamoDBValidator:
    def test_dynamodb_without_hash_key_raises(self):
        """DynamoDB resource without hash_key in config raises ValidationError."""
        payload = {
            "project_name": "dynamo-test",
            "environments": [_make_env()],
            "resources": [
                {
                    "name": "my-table",
                    "service_type": "dynamodb",
                    "config": {"billing_mode": "PAY_PER_REQUEST"},
                },
            ],
        }
        with pytest.raises(ValidationError) as exc_info:
            ArchitectureDescription(**payload)
        assert "hash_key" in str(exc_info.value)

    def test_dynamodb_with_hash_key_passes(self):
        """DynamoDB resource WITH hash_key passes validation."""
        payload = {
            "project_name": "dynamo-test",
            "environments": [_make_env()],
            "resources": [
                _make_resource("my-table", "dynamodb"),
            ],
        }
        desc = ArchitectureDescription(**payload)
        assert desc.resources[0].config.hash_key == "id"


# ---------------------------------------------------------------------------
# 8. HCL Renderer unit tests
# ---------------------------------------------------------------------------

from app.generators.hcl_renderer import HCLRenderer


class TestHCLRenderer:
    """Unit tests for the HCLRenderer class.

    Validates: Requirements 5.1, 5.3, 5.4, 5.5
    """

    def setup_method(self):
        self.renderer = HCLRenderer()

    # -- render_resource: flat attributes ----------------------------------

    def test_render_resource_flat_attrs(self):
        """render_resource produces correct HCL for simple flat attributes."""
        result = self.renderer.render_resource(
            "aws_s3_bucket", "my_bucket", {"bucket": "my-bucket-name"}
        )
        expected = (
            'resource "aws_s3_bucket" "my_bucket" {\n  bucket = "my-bucket-name"\n}\n'
        )
        assert result == expected

    # -- render_resource: nested dict attributes ---------------------------

    def test_render_resource_nested_dict(self):
        """render_resource renders nested dict attributes as nested blocks with correct indentation."""
        result = self.renderer.render_resource(
            "aws_dynamodb_table",
            "my_table",
            {
                "name": "my-table",
                "attribute": {"name": "id", "type": "S"},
            },
        )
        expected = (
            'resource "aws_dynamodb_table" "my_table" {\n'
            '  name = "my-table"\n'
            "  attribute {\n"
            '    name = "id"\n'
            '    type = "S"\n'
            "  }\n"
            "}\n"
        )
        assert result == expected

    # -- render_resource: repeated nested blocks (list of dicts) -----------

    def test_render_resource_repeated_nested_blocks(self):
        """render_resource renders a list of dicts as repeated nested blocks."""
        result = self.renderer.render_resource(
            "aws_dynamodb_table",
            "my_table",
            {
                "name": "my-table",
                "attribute": [
                    {"name": "id", "type": "S"},
                    {"name": "sort_key", "type": "N"},
                ],
            },
        )
        assert 'name = "my-table"' in result
        # Two separate attribute blocks
        assert result.count("attribute {") == 2
        assert '    name = "id"' in result
        assert '    name = "sort_key"' in result

    # -- render_variable: without default ----------------------------------

    def test_render_variable_no_default(self):
        """render_variable produces a variable block with description and type, no default."""
        result = self.renderer.render_variable(
            "region", "string", "AWS region to deploy into"
        )
        expected = (
            'variable "region" {\n'
            '  description = "AWS region to deploy into"\n'
            "  type        = string\n"
            "}\n"
        )
        assert result == expected

    # -- render_variable: with default -------------------------------------

    def test_render_variable_with_default(self):
        """render_variable includes a default attribute when provided."""
        result = self.renderer.render_variable(
            "region", "string", "AWS region", default="us-east-1"
        )
        expected = (
            'variable "region" {\n'
            '  description = "AWS region"\n'
            "  type        = string\n"
            '  default     = "us-east-1"\n'
            "}\n"
        )
        assert result == expected

    # -- render_output -----------------------------------------------------

    def test_render_output(self):
        """render_output produces an output block with description and value."""
        result = self.renderer.render_output(
            "bucket_arn",
            "aws_s3_bucket.my_bucket.arn",
            "ARN of the S3 bucket",
        )
        expected = (
            'output "bucket_arn" {\n'
            '  description = "ARN of the S3 bucket"\n'
            "  value       = aws_s3_bucket.my_bucket.arn\n"
            "}\n"
        )
        assert result == expected

    # -- render_module -----------------------------------------------------

    def test_render_module(self):
        """render_module produces a module block with source and variable assignments."""
        result = self.renderer.render_module(
            "lambda",
            "./modules/lambda",
            {"function_name": "var.function_name", "runtime": "var.runtime"},
        )
        expected = (
            'module "lambda" {\n'
            '  source = "./modules/lambda"\n'
            "  function_name = var.function_name\n"
            "  runtime = var.runtime\n"
            "}\n"
        )
        assert result == expected

    # -- render_provider ---------------------------------------------------

    def test_render_provider(self):
        """render_provider produces a provider block with region."""
        result = self.renderer.render_provider("aws", "us-west-2")
        expected = 'provider "aws" {\n  region = "us-west-2"\n}\n'
        assert result == expected

    # -- _quote: special characters ----------------------------------------

    def test_quote_escapes_double_quotes(self):
        """_quote escapes embedded double quotes."""
        assert HCLRenderer._quote('say "hello"') == '"say \\"hello\\""'

    def test_quote_escapes_backslashes(self):
        """_quote escapes backslashes before escaping quotes."""
        assert HCLRenderer._quote("path\\to\\file") == '"path\\\\to\\\\file"'

    def test_quote_escapes_backslash_and_quote_together(self):
        """_quote handles strings with both backslashes and quotes."""
        assert HCLRenderer._quote('a\\"b') == '"a\\\\\\"b"'

    # -- _format_value: Terraform references not quoted --------------------

    def test_format_value_var_reference_unquoted(self):
        """Strings starting with 'var.' are passed through unquoted."""
        assert HCLRenderer._format_value("var.region") == "var.region"

    def test_format_value_module_reference_unquoted(self):
        """Strings starting with 'module.' are passed through unquoted."""
        assert HCLRenderer._format_value("module.lambda.arn") == "module.lambda.arn"

    def test_format_value_aws_resource_reference_unquoted(self):
        """Strings starting with 'aws_' are passed through unquoted."""
        assert (
            HCLRenderer._format_value("aws_lambda_function.my_func.arn")
            == "aws_lambda_function.my_func.arn"
        )

    def test_format_value_local_reference_unquoted(self):
        """Strings starting with 'local.' are passed through unquoted."""
        assert HCLRenderer._format_value("local.name") == "local.name"

    def test_format_value_data_reference_unquoted(self):
        """Strings starting with 'data.' are passed through unquoted."""
        assert (
            HCLRenderer._format_value("data.aws_region.current.name")
            == "data.aws_region.current.name"
        )

    def test_format_value_plain_string_quoted(self):
        """Plain strings are wrapped in double quotes."""
        assert HCLRenderer._format_value("hello") == '"hello"'

    # -- _format_value: booleans and numbers -------------------------------

    def test_format_value_bool_true(self):
        """Boolean True renders as 'true'."""
        assert HCLRenderer._format_value(True) == "true"

    def test_format_value_bool_false(self):
        """Boolean False renders as 'false'."""
        assert HCLRenderer._format_value(False) == "false"

    def test_format_value_integer(self):
        """Integers render as unquoted numbers."""
        assert HCLRenderer._format_value(42) == "42"

    def test_format_value_float(self):
        """Floats render as unquoted numbers."""
        assert HCLRenderer._format_value(3.14) == "3.14"

    # -- _format_value: lists ----------------------------------------------

    def test_format_value_list_of_strings(self):
        """Lists of strings render as HCL list syntax."""
        assert HCLRenderer._format_value(["a", "b", "c"]) == '["a", "b", "c"]'

    def test_format_value_list_of_numbers(self):
        """Lists of numbers render correctly."""
        assert HCLRenderer._format_value([1, 2, 3]) == "[1, 2, 3]"

    def test_format_value_empty_list(self):
        """Empty lists render as []."""
        assert HCLRenderer._format_value([]) == "[]"

    def test_format_value_mixed_list(self):
        """Lists with mixed types render each element correctly."""
        assert HCLRenderer._format_value([True, 1, "x"]) == '[true, 1, "x"]'
