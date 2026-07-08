"""Lambda service generator — produces HCL for aws_lambda_function and IAM resources."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.lambda_config import LambdaConfig
from app.models.ir_models import ResourceInstanceIR


class LambdaGenerator:
    """Generates Terraform files for Lambda functions and layers."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def _resolve_config(self, instance: ResourceInstanceIR) -> LambdaConfig:
        """Resolve instance config to LambdaConfig.

        Uses get_typed_config when the config is already a LambdaConfig.
        Falls back to duck-typed access if field names match.
        """
        try:
            return get_typed_config(instance, LambdaConfig)
        except Exception:
            # Fallback: duck-typed access works if field names match.
            return instance.config  # type: ignore[return-value]

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate lambda.tf with aws_lambda_function resource."""
        config = self._resolve_config(instance)
        attrs: dict = {
            "function_name": "var.function_name",
            "role": f"aws_iam_role.{instance.name}_role.arn",
        }

        # Handle package_type conditional: when Image, skip handler/runtime
        if config.package_type == "Image":
            attrs["package_type"] = "var.package_type"
            if config.image_uri is not None:
                attrs["image_uri"] = "var.image_uri"
            if config.image_config is not None:
                image_config_block: dict = {}
                if "entry_point" in config.image_config:
                    image_config_block["entry_point"] = "var.image_config_entry_point"
                if "command" in config.image_config:
                    image_config_block["command"] = "var.image_config_command"
                if "working_directory" in config.image_config:
                    image_config_block["working_directory"] = (
                        "var.image_config_working_directory"
                    )
                if image_config_block:
                    attrs["image_config"] = image_config_block
        else:
            attrs["handler"] = "var.handler"
            attrs["runtime"] = "var.runtime"
            if config.package_type is not None:
                attrs["package_type"] = "var.package_type"

        # Existing optional fields
        if config.memory_size is not None:
            attrs["memory_size"] = "var.memory_size"
        if config.timeout is not None:
            attrs["timeout"] = "var.timeout"
        if config.description is not None:
            attrs["description"] = "var.description"
        if config.architectures is not None:
            attrs["architectures"] = ["var.architectures"]
        if config.ephemeral_storage_size is not None:
            attrs["ephemeral_storage"] = {"size": "var.ephemeral_storage_size"}
        if config.reserved_concurrent_executions is not None:
            attrs["reserved_concurrent_executions"] = (
                "var.reserved_concurrent_executions"
            )
        if config.publish is not None:
            attrs["publish"] = "var.publish"
        if config.layers is not None:
            attrs["layers"] = "var.layers"
        if config.environment_variables is not None:
            attrs["environment"] = {"variables": "var.environment_variables"}
        if config.tags is not None:
            attrs["tags"] = "var.tags"

        # Deployment source fields
        if config.s3_bucket is not None:
            attrs["s3_bucket"] = "var.s3_bucket"
        if config.s3_key is not None:
            attrs["s3_key"] = "var.s3_key"
        if config.s3_object_version is not None:
            attrs["s3_object_version"] = "var.s3_object_version"
        if config.source_code_hash is not None:
            attrs["source_code_hash"] = "var.source_code_hash"
        if config.filename is not None:
            attrs["filename"] = "var.filename"

        # VPC config block
        if (
            config.vpc_subnet_ids is not None
            and config.vpc_security_group_ids is not None
        ):
            attrs["vpc_config"] = {
                "subnet_ids": "var.vpc_subnet_ids",
                "security_group_ids": "var.vpc_security_group_ids",
            }

        # Tracing config block
        if config.tracing_mode is not None:
            attrs["tracing_config"] = {"mode": "var.tracing_mode"}

        # Dead letter config block
        if config.dead_letter_target_arn is not None:
            attrs["dead_letter_config"] = {
                "target_arn": "var.dead_letter_target_arn",
            }

        # KMS key ARN
        if config.kms_key_arn is not None:
            attrs["kms_key_arn"] = "var.kms_key_arn"

        # File system config block
        if (
            config.file_system_arn is not None
            and config.file_system_local_mount_path is not None
        ):
            attrs["file_system_config"] = {
                "arn": "var.file_system_arn",
                "local_mount_path": "var.file_system_local_mount_path",
            }

        # Snap start block
        if config.snap_start_apply_on is not None:
            attrs["snap_start"] = {"apply_on": "var.snap_start_apply_on"}

        # Logging config block
        logging_block: dict = {}
        if config.logging_log_format is not None:
            logging_block["log_format"] = "var.logging_log_format"
        if config.logging_log_group is not None:
            logging_block["log_group"] = "var.logging_log_group"
        if config.logging_application_log_level is not None:
            logging_block["application_log_level"] = "var.logging_application_log_level"
        if config.logging_system_log_level is not None:
            logging_block["system_log_level"] = "var.logging_system_log_level"
        if logging_block:
            attrs["logging_config"] = logging_block

        # Code signing config ARN
        if config.code_signing_config_arn is not None:
            attrs["code_signing_config_arn"] = "var.code_signing_config_arn"

        return self._r.render_resource("aws_lambda_function", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Lambda instance."""
        config = self._resolve_config(instance)

        # function_name is always required (no default)
        parts = [
            self._r.render_variable(
                "function_name", "string", "Name of the Lambda function"
            ),
        ]

        # handler/runtime: required when package_type is Zip/None, not emitted for Image
        if config.package_type != "Image":
            parts.append(
                self._r.render_variable("handler", "string", "Lambda function handler")
            )
            parts.append(
                self._r.render_variable("runtime", "string", "Lambda function runtime")
            )

        # package_type
        if config.package_type is not None:
            parts.append(
                self._r.render_variable(
                    "package_type",
                    "string",
                    "Lambda deployment package type",
                    default=config.package_type,
                )
            )

        # Image-specific fields
        if config.image_uri is not None:
            parts.append(
                self._r.render_variable(
                    "image_uri",
                    "string",
                    "ECR image URI for container-based Lambda",
                    default=config.image_uri,
                )
            )
        if config.image_config is not None:
            if "entry_point" in config.image_config:
                parts.append(
                    self._r.render_variable(
                        "image_config_entry_point",
                        "list(string)",
                        "Container image entry point override",
                        default=config.image_config["entry_point"],
                    )
                )
            if "command" in config.image_config:
                parts.append(
                    self._r.render_variable(
                        "image_config_command",
                        "list(string)",
                        "Container image command override",
                        default=config.image_config["command"],
                    )
                )
            if "working_directory" in config.image_config:
                parts.append(
                    self._r.render_variable(
                        "image_config_working_directory",
                        "string",
                        "Container image working directory override",
                        default=config.image_config["working_directory"],
                    )
                )

        # Existing optional fields
        if config.memory_size is not None:
            parts.append(
                self._r.render_variable(
                    "memory_size",
                    "number",
                    "Lambda memory size in MB",
                    default=config.memory_size,
                )
            )
        if config.timeout is not None:
            parts.append(
                self._r.render_variable(
                    "timeout",
                    "number",
                    "Lambda timeout in seconds",
                    default=config.timeout,
                )
            )
        if config.description is not None:
            parts.append(
                self._r.render_variable(
                    "description",
                    "string",
                    "Description of the Lambda function",
                    default=config.description,
                )
            )
        if config.architectures is not None:
            parts.append(
                self._r.render_variable(
                    "architectures",
                    "string",
                    "Instruction set architecture for the function",
                    default=config.architectures,
                )
            )
        if config.ephemeral_storage_size is not None:
            parts.append(
                self._r.render_variable(
                    "ephemeral_storage_size",
                    "number",
                    "Size of the function /tmp directory in MB",
                    default=config.ephemeral_storage_size,
                )
            )
        if config.reserved_concurrent_executions is not None:
            parts.append(
                self._r.render_variable(
                    "reserved_concurrent_executions",
                    "number",
                    "Number of reserved concurrent executions",
                    default=config.reserved_concurrent_executions,
                )
            )
        if config.publish is not None:
            parts.append(
                self._r.render_variable(
                    "publish",
                    "bool",
                    "Whether to publish as a new Lambda function version",
                    default=config.publish,
                )
            )
        if config.layers is not None:
            parts.append(
                self._r.render_variable(
                    "layers",
                    "list(string)",
                    "List of Lambda layer ARNs to attach",
                    default=config.layers,
                )
            )

        # Deployment source fields
        if config.s3_bucket is not None:
            parts.append(
                self._r.render_variable(
                    "s3_bucket",
                    "string",
                    "S3 bucket containing the function deployment package",
                    default=config.s3_bucket,
                )
            )
        if config.s3_key is not None:
            parts.append(
                self._r.render_variable(
                    "s3_key",
                    "string",
                    "S3 object key of the function deployment package",
                    default=config.s3_key,
                )
            )
        if config.s3_object_version is not None:
            parts.append(
                self._r.render_variable(
                    "s3_object_version",
                    "string",
                    "S3 object version of the function deployment package",
                    default=config.s3_object_version,
                )
            )
        if config.source_code_hash is not None:
            parts.append(
                self._r.render_variable(
                    "source_code_hash",
                    "string",
                    "Base64-encoded SHA256 hash of the deployment package",
                    default=config.source_code_hash,
                )
            )
        if config.filename is not None:
            parts.append(
                self._r.render_variable(
                    "filename",
                    "string",
                    "Path to the function deployment package",
                    default=config.filename,
                )
            )

        # VPC fields
        if config.vpc_subnet_ids is not None:
            parts.append(
                self._r.render_variable(
                    "vpc_subnet_ids",
                    "list(string)",
                    "List of subnet IDs for VPC configuration",
                    default=config.vpc_subnet_ids,
                )
            )
        if config.vpc_security_group_ids is not None:
            parts.append(
                self._r.render_variable(
                    "vpc_security_group_ids",
                    "list(string)",
                    "List of security group IDs for VPC configuration",
                    default=config.vpc_security_group_ids,
                )
            )

        # Tracing
        if config.tracing_mode is not None:
            parts.append(
                self._r.render_variable(
                    "tracing_mode",
                    "string",
                    "X-Ray tracing mode for the function",
                    default=config.tracing_mode,
                )
            )

        # Dead letter config
        if config.dead_letter_target_arn is not None:
            parts.append(
                self._r.render_variable(
                    "dead_letter_target_arn",
                    "string",
                    "ARN of the dead letter queue for failed invocations",
                    default=config.dead_letter_target_arn,
                )
            )

        # Encryption
        if config.kms_key_arn is not None:
            parts.append(
                self._r.render_variable(
                    "kms_key_arn",
                    "string",
                    "KMS key ARN for environment variable encryption",
                    default=config.kms_key_arn,
                )
            )

        # File system
        if config.file_system_arn is not None:
            parts.append(
                self._r.render_variable(
                    "file_system_arn",
                    "string",
                    "ARN of the EFS access point for the function",
                    default=config.file_system_arn,
                )
            )
        if config.file_system_local_mount_path is not None:
            parts.append(
                self._r.render_variable(
                    "file_system_local_mount_path",
                    "string",
                    "Local mount path for the EFS file system",
                    default=config.file_system_local_mount_path,
                )
            )

        # Snap start
        if config.snap_start_apply_on is not None:
            parts.append(
                self._r.render_variable(
                    "snap_start_apply_on",
                    "string",
                    "SnapStart setting for the function",
                    default=config.snap_start_apply_on,
                )
            )

        # Logging config
        if config.logging_log_format is not None:
            parts.append(
                self._r.render_variable(
                    "logging_log_format",
                    "string",
                    "Log format for the function",
                    default=config.logging_log_format,
                )
            )
        if config.logging_log_group is not None:
            parts.append(
                self._r.render_variable(
                    "logging_log_group",
                    "string",
                    "CloudWatch log group for the function",
                    default=config.logging_log_group,
                )
            )
        if config.logging_application_log_level is not None:
            parts.append(
                self._r.render_variable(
                    "logging_application_log_level",
                    "string",
                    "Application log level for the function",
                    default=config.logging_application_log_level,
                )
            )
        if config.logging_system_log_level is not None:
            parts.append(
                self._r.render_variable(
                    "logging_system_log_level",
                    "string",
                    "System log level for the function",
                    default=config.logging_system_log_level,
                )
            )

        # Code signing config
        if config.code_signing_config_arn is not None:
            parts.append(
                self._r.render_variable(
                    "code_signing_config_arn",
                    "string",
                    "ARN of the code signing configuration",
                    default=config.code_signing_config_arn,
                )
            )

        # Environment variables and tags
        if config.environment_variables is not None:
            parts.append(
                self._r.render_variable(
                    "environment_variables",
                    "map(string)",
                    "Environment variables for the Lambda function",
                )
            )
        if config.tags is not None:
            parts.append(
                self._r.render_variable(
                    "tags",
                    "map(string)",
                    "Tags to apply to the Lambda function",
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Lambda instance."""
        parts = [
            self._r.render_output(
                "function_arn",
                f"aws_lambda_function.{instance.name}.arn",
                "ARN of the Lambda function",
            ),
            self._r.render_output(
                "function_name",
                f"aws_lambda_function.{instance.name}.function_name",
                "Name of the Lambda function",
            ),
        ]
        return "\n".join(parts)

    def generate_iam_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate iam.tf with IAM role and policy referencing iam-policies/ via file()."""
        safe_name = instance.name
        # IAM role
        role_attrs = {
            "name": f"{safe_name}-role",
            "assume_role_policy": 'jsonencode({\n    Version = "2012-10-17"\n    Statement = [{\n      Action = "sts:AssumeRole"\n      Effect = "Allow"\n      Principal = { Service = "lambda.amazonaws.com" }\n    }]\n  })',
        }
        role_block = self._r.render_resource(
            "aws_iam_role", f"{safe_name}_role", role_attrs
        )

        # IAM policy referencing the JSON file via file()
        policy_path = f"${{path.root}}/../../iam-policies/{safe_name}-policy.json"
        policy_attrs = {
            "name": f"{safe_name}-policy",
            "role": f"aws_iam_role.{safe_name}_role.id",
            "policy": f'file("{policy_path}")',
        }
        policy_block = self._r.render_resource(
            "aws_iam_role_policy", f"{safe_name}_policy", policy_attrs
        )

        return role_block + "\n" + policy_block
