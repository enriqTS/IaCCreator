"""Native Batch job container properties and secret environment bindings."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.batch_job_definition_config import BatchJobDefinitionConfig
from app.models.ir_models import ResourceInstanceIR


class BatchJobDefinitionGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, BatchJobDefinitionConfig)
        secrets = (
            "merge(var.external_secrets, local.runtime_secrets)"
            if config._inject_runtime_secrets
            else "var.external_secrets"
        )
        content = f"locals {{\n  batch_job_secrets = {secrets}\n}}\n"
        container = {
            "image": Expr("var.image"),
            "command": Expr("var.command"),
            "resourceRequirements": [
                {"type": "VCPU", "value": Expr("tostring(var.vcpus)")},
                {"type": "MEMORY", "value": Expr("tostring(var.memory_mib)")},
            ],
            "environment": Expr(
                "[for name, value in var.environment_variables : { name = name, value = value } if !contains(keys(local.batch_job_secrets), name)]"
            ),
            "secrets": Expr(
                "[for name, value in local.batch_job_secrets : { name = name, valueFrom = value }]"
            ),
        }
        if config.execution_role_arn:
            container["executionRoleArn"] = Expr("var.execution_role_arn")
        if config.job_role_arn:
            container["jobRoleArn"] = Expr("var.job_role_arn")
        attrs = {
            "name": instance.name,
            "type": "container",
            "platform_capabilities": ["EC2"],
            "container_properties": self._r.render_json_policy(container),
        }
        if config._inject_runtime_secrets:
            attrs["depends_on"] = Expr("[aws_iam_role_policy.runtime_secrets]")
        return content + self._r.render_resource(
            "aws_batch_job_definition", instance.name, attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, BatchJobDefinitionConfig)
        types = {"map": "map(string)", "list": "list(string)"}
        return "\n".join(
            self._r.render_variable(
                field.name, types.get(field.type, field.type), field.description
            )
            for field in config.get_variable_schema()
            if getattr(config, field.name) is not None
        )

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_batch_job_definition.{instance.name}"
        return "\n".join(
            self._r.render_output(name, f"{ref}.{attribute}", description)
            for name, attribute, description in (
                (
                    "job_definition_arn",
                    "arn",
                    "Revision-qualified Batch job definition ARN",
                ),
                ("job_definition_name", "name", "Batch job definition name"),
                ("revision", "revision", "Batch job definition revision"),
            )
        )
