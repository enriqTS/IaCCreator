"""Unit tests for LambdaGenerator new fields.

Requirements: 1.14, 5.1
"""

import pytest

from app.generators.lambda_generator import LambdaGenerator
from app.models.input_models._general import ServiceType
from app.models.input_models.lambda_config import LambdaConfig
from app.models.ir_models import ResourceInstanceIR


def _make_lambda_instance(
    name: str = "test_lambda",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for Lambda."""
    # Ensure required fields have defaults for Zip package type
    config_kwargs.setdefault("function_name", "my_function")
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.LAMBDA,
        config=LambdaConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> LambdaGenerator:
    return LambdaGenerator()


# ---------------------------------------------------------------------------
# VPC config block
# ---------------------------------------------------------------------------


class TestVpcConfig:
    """Test VPC config block emission when vpc_subnet_ids/vpc_security_group_ids set."""

    def test_vpc_config_block_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            vpc_subnet_ids=["subnet-abc123"],
            vpc_security_group_ids=["sg-abc123"],
        )
        result = gen.generate_resource_tf(instance)
        assert "vpc_config" in result
        assert "subnet_ids" in result
        assert "security_group_ids" in result

    def test_vpc_config_not_emitted_when_missing(self, gen: LambdaGenerator):
        instance = _make_lambda_instance()
        result = gen.generate_resource_tf(instance)
        assert "vpc_config" not in result

    def test_vpc_variables_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            vpc_subnet_ids=["subnet-abc123"],
            vpc_security_group_ids=["sg-abc123"],
        )
        result = gen.generate_variables_tf(instance)
        assert "vpc_subnet_ids" in result
        assert "vpc_security_group_ids" in result


# ---------------------------------------------------------------------------
# Tracing config block
# ---------------------------------------------------------------------------


class TestTracingConfig:
    """Test tracing_config block emission when tracing_mode set."""

    def test_tracing_config_block_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(tracing_mode="Active")
        result = gen.generate_resource_tf(instance)
        assert "tracing_config" in result
        assert "mode" in result

    def test_tracing_config_not_emitted_when_missing(self, gen: LambdaGenerator):
        instance = _make_lambda_instance()
        result = gen.generate_resource_tf(instance)
        assert "tracing_config" not in result

    def test_tracing_variable_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(tracing_mode="PassThrough")
        result = gen.generate_variables_tf(instance)
        assert "tracing_mode" in result


# ---------------------------------------------------------------------------
# Dead letter config
# ---------------------------------------------------------------------------


class TestDeadLetterConfig:
    """Test dead_letter_config emission when dead_letter_target_arn set."""

    def test_dead_letter_config_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            dead_letter_target_arn="arn:aws:sqs:us-east-1:123456789012:dlq"
        )
        result = gen.generate_resource_tf(instance)
        assert "dead_letter_config" in result
        assert "target_arn" in result

    def test_dead_letter_config_not_emitted_when_missing(self, gen: LambdaGenerator):
        instance = _make_lambda_instance()
        result = gen.generate_resource_tf(instance)
        assert "dead_letter_config" not in result

    def test_dead_letter_variable_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            dead_letter_target_arn="arn:aws:sns:us-east-1:123456789012:topic"
        )
        result = gen.generate_variables_tf(instance)
        assert "dead_letter_target_arn" in result


# ---------------------------------------------------------------------------
# Logging config block
# ---------------------------------------------------------------------------


class TestLoggingConfig:
    """Test logging_config block emission when logging fields set."""

    def test_logging_config_emitted_with_log_format(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(logging_log_format="JSON")
        result = gen.generate_resource_tf(instance)
        assert "logging_config" in result
        assert "log_format" in result

    def test_logging_config_emitted_with_all_fields(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            logging_log_format="JSON",
            logging_log_group="/aws/lambda/my-func",
            logging_application_log_level="INFO",
            logging_system_log_level="WARN",
        )
        result = gen.generate_resource_tf(instance)
        assert "logging_config" in result
        assert "log_format" in result
        assert "log_group" in result
        assert "application_log_level" in result
        assert "system_log_level" in result

    def test_logging_config_not_emitted_when_missing(self, gen: LambdaGenerator):
        instance = _make_lambda_instance()
        result = gen.generate_resource_tf(instance)
        assert "logging_config" not in result

    def test_logging_variables_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            logging_log_format="Text",
            logging_log_group="/aws/lambda/func",
            logging_application_log_level="DEBUG",
            logging_system_log_level="INFO",
        )
        result = gen.generate_variables_tf(instance)
        assert "logging_log_format" in result
        assert "logging_log_group" in result
        assert "logging_application_log_level" in result
        assert "logging_system_log_level" in result


# ---------------------------------------------------------------------------
# Snap start block
# ---------------------------------------------------------------------------


class TestSnapStart:
    """Test snap_start block emission when snap_start_apply_on set."""

    def test_snap_start_block_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(snap_start_apply_on="PublishedVersions")
        result = gen.generate_resource_tf(instance)
        assert "snap_start" in result
        assert "apply_on" in result

    def test_snap_start_not_emitted_when_missing(self, gen: LambdaGenerator):
        instance = _make_lambda_instance()
        result = gen.generate_resource_tf(instance)
        assert "snap_start" not in result

    def test_snap_start_variable_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(snap_start_apply_on="PublishedVersions")
        result = gen.generate_variables_tf(instance)
        assert "snap_start_apply_on" in result


# ---------------------------------------------------------------------------
# File system config
# ---------------------------------------------------------------------------


class TestFileSystemConfig:
    """Test file_system_config emission when file_system fields set."""

    def test_file_system_config_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            file_system_arn="arn:aws:elasticfilesystem:us-east-1:123456789012:access-point/fsap-abc123",
            file_system_local_mount_path="/mnt/efs",
        )
        result = gen.generate_resource_tf(instance)
        assert "file_system_config" in result
        assert "local_mount_path" in result

    def test_file_system_config_not_emitted_when_missing(self, gen: LambdaGenerator):
        instance = _make_lambda_instance()
        result = gen.generate_resource_tf(instance)
        assert "file_system_config" not in result

    def test_file_system_variables_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            file_system_arn="arn:aws:elasticfilesystem:us-east-1:123456789012:access-point/fsap-abc123",
            file_system_local_mount_path="/mnt/data",
        )
        result = gen.generate_variables_tf(instance)
        assert "file_system_arn" in result
        assert "file_system_local_mount_path" in result


# ---------------------------------------------------------------------------
# Image package_type skips handler/runtime
# ---------------------------------------------------------------------------


class TestImagePackageType:
    """Test Image package_type skips handler/runtime in resource block."""

    def test_image_skips_handler_runtime(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            package_type="Image",
            image_uri="123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo:latest",
            handler=None,
            runtime=None,
        )
        result = gen.generate_resource_tf(instance)
        assert "handler" not in result
        assert "runtime" not in result
        assert "package_type" in result
        assert "image_uri" in result

    def test_image_variables_skip_handler_runtime(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            package_type="Image",
            image_uri="123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo:latest",
            handler=None,
            runtime=None,
        )
        result = gen.generate_variables_tf(instance)
        # handler/runtime should NOT appear for Image package type
        # But function_name should still be there
        assert "function_name" in result
        assert "var.handler" not in result
        # The variable "handler" should not be defined for Image
        lines = result.split("\n")
        handler_var_lines = [l for l in lines if '"handler"' in l and "variable" in l]
        assert len(handler_var_lines) == 0

    def test_zip_includes_handler_runtime(self, gen: LambdaGenerator):
        instance = _make_lambda_instance()
        result = gen.generate_resource_tf(instance)
        assert "handler" in result
        assert "runtime" in result


# ---------------------------------------------------------------------------
# Deployment source fields in variables output
# ---------------------------------------------------------------------------


class TestDeploymentSourceVariables:
    """Test deployment source fields (s3_bucket, s3_key, etc.) in variables output."""

    def test_s3_bucket_variable_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(s3_bucket="my-deployment-bucket")
        result = gen.generate_variables_tf(instance)
        assert "s3_bucket" in result

    def test_s3_key_variable_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(s3_key="lambda/my_function.zip")
        result = gen.generate_variables_tf(instance)
        assert "s3_key" in result

    def test_s3_object_version_variable_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(s3_object_version="abc123")
        result = gen.generate_variables_tf(instance)
        assert "s3_object_version" in result

    def test_source_code_hash_variable_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(source_code_hash="abc123hash")
        result = gen.generate_variables_tf(instance)
        assert "source_code_hash" in result

    def test_filename_variable_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(filename="lambda.zip")
        result = gen.generate_variables_tf(instance)
        assert "filename" in result

    def test_deployment_source_fields_in_resource(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            s3_bucket="my-bucket",
            s3_key="lambda/func.zip",
            s3_object_version="v1",
            source_code_hash="hash123",
        )
        result = gen.generate_resource_tf(instance)
        assert "s3_bucket" in result
        assert "s3_key" in result
        assert "s3_object_version" in result
        assert "source_code_hash" in result


# ---------------------------------------------------------------------------
# Function URL generation
# ---------------------------------------------------------------------------


class TestFunctionUrl:
    """Test aws_lambda_function_url resource emission."""

    def test_function_url_emitted_with_none_auth(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            function_url_config={"authorization_type": "NONE"}
        )
        result = gen.generate_resource_tf(instance)
        assert "aws_lambda_function_url" in result
        assert "authorization_type" in result
        assert "NONE" in result
        assert "function_name" in result

    def test_function_url_emitted_with_aws_iam_auth(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            function_url_config={"authorization_type": "AWS_IAM"}
        )
        result = gen.generate_resource_tf(instance)
        assert "aws_lambda_function_url" in result
        assert "AWS_IAM" in result

    def test_function_url_with_cors_block(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            function_url_config={
                "authorization_type": "NONE",
                "cors": {
                    "allow_origins": ["https://example.com"],
                    "allow_methods": ["GET", "POST"],
                    "allow_headers": ["Content-Type"],
                    "expose_headers": ["X-Custom"],
                    "max_age": 3600,
                    "allow_credentials": True,
                },
            }
        )
        result = gen.generate_resource_tf(instance)
        assert "cors" in result
        assert "allow_origins" in result
        assert "allow_methods" in result
        assert "allow_headers" in result
        assert "expose_headers" in result
        assert "max_age" in result
        assert "allow_credentials" in result

    def test_function_url_without_cors(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            function_url_config={"authorization_type": "NONE"}
        )
        result = gen.generate_resource_tf(instance)
        assert "cors" not in result

    def test_function_url_not_emitted_when_missing(self, gen: LambdaGenerator):
        instance = _make_lambda_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_lambda_function_url" not in result

    def test_function_url_output_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            function_url_config={"authorization_type": "NONE"}
        )
        result = gen.generate_outputs_tf(instance)
        assert "function_url" in result

    def test_function_url_output_not_emitted_when_missing(self, gen: LambdaGenerator):
        instance = _make_lambda_instance()
        result = gen.generate_outputs_tf(instance)
        assert "function_url" not in result


# ---------------------------------------------------------------------------
# Provisioned concurrency generation
# ---------------------------------------------------------------------------


class TestProvisionedConcurrency:
    """Test aws_lambda_provisioned_concurrency_config resource emission."""

    def test_provisioned_concurrency_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            publish=True,
            provisioned_concurrency_config={
                "provisioned_concurrent_executions": 10,
            },
        )
        result = gen.generate_resource_tf(instance)
        assert "aws_lambda_provisioned_concurrency_config" in result
        assert "function_name" in result
        assert "qualifier" in result
        assert "provisioned_concurrent_executions" in result

    def test_provisioned_concurrency_references_function(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            name="my_func",
            publish=True,
            provisioned_concurrency_config={
                "provisioned_concurrent_executions": 5,
            },
        )
        result = gen.generate_resource_tf(instance)
        assert "aws_lambda_function.my_func.function_name" in result
        assert "aws_lambda_function.my_func.version" in result

    def test_provisioned_concurrency_not_emitted_when_missing(
        self, gen: LambdaGenerator
    ):
        instance = _make_lambda_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_lambda_provisioned_concurrency_config" not in result


# ---------------------------------------------------------------------------
# Runtime management config block
# ---------------------------------------------------------------------------


class TestRuntimeManagementConfig:
    """Test runtime_management_config block within aws_lambda_function."""

    def test_runtime_management_auto_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            runtime_management_config={"update_runtime_on": "Auto"}
        )
        result = gen.generate_resource_tf(instance)
        assert "runtime_management_config" in result
        assert "update_runtime_on" in result

    def test_runtime_management_manual_includes_arn(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            runtime_management_config={
                "update_runtime_on": "Manual",
                "runtime_version_arn": "arn:aws:lambda:us-east-1::runtime:python3.12:v42",
            }
        )
        result = gen.generate_resource_tf(instance)
        assert "runtime_management_config" in result
        assert "update_runtime_on" in result
        assert "runtime_version_arn" in result

    def test_runtime_management_function_update_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            runtime_management_config={"update_runtime_on": "FunctionUpdate"}
        )
        result = gen.generate_resource_tf(instance)
        assert "runtime_management_config" in result
        assert "update_runtime_on" in result

    def test_runtime_management_not_emitted_when_missing(self, gen: LambdaGenerator):
        instance = _make_lambda_instance()
        result = gen.generate_resource_tf(instance)
        assert "runtime_management_config" not in result

    def test_runtime_management_variables_emitted(self, gen: LambdaGenerator):
        instance = _make_lambda_instance(
            runtime_management_config={"update_runtime_on": "Auto"}
        )
        result = gen.generate_variables_tf(instance)
        assert "runtime_management_update_runtime_on" in result

    def test_runtime_management_manual_variables_include_arn(
        self, gen: LambdaGenerator
    ):
        instance = _make_lambda_instance(
            runtime_management_config={
                "update_runtime_on": "Manual",
                "runtime_version_arn": "arn:aws:lambda:us-east-1::runtime:python3.12:v42",
            }
        )
        result = gen.generate_variables_tf(instance)
        assert "runtime_management_update_runtime_on" in result
        assert "runtime_management_runtime_version_arn" in result
