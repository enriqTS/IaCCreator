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
            "handler": "var.handler",
            "runtime": "var.runtime",
        }
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

        return self._r.render_resource("aws_lambda_function", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Lambda instance."""
        config = self._resolve_config(instance)
        parts = [
            self._r.render_variable(
                "function_name", "string", "Name of the Lambda function"
            ),
            self._r.render_variable("handler", "string", "Lambda function handler"),
            self._r.render_variable("runtime", "string", "Lambda function runtime"),
        ]
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
