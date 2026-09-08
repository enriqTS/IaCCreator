"""App Runner service generator — produces HCL for aws_apprunner_service resources."""

import json

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.app_runner_config import AppRunnerConfig
from app.models.ir_models import ResourceInstanceIR


class AppRunnerGenerator:
    """Generates Terraform files for App Runner services."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_apprunner_service resource."""
        config = get_typed_config(instance, AppRunnerConfig)

        attrs: dict = {
            "service_name": Expr("var.service_name"),
            "source_configuration": {
                "image_repository": {
                    "image_identifier": Expr("var.image_identifier"),
                    "image_repository_type": Expr("var.image_repository_type"),
                    "image_configuration": {
                        "runtime_environment_secrets": Expr(
                            "merge(var.runtime_environment_secrets, local.runtime_secrets)"
                            if config._inject_runtime_secrets
                            else "var.runtime_environment_secrets"
                        ),
                    },
                },
            },
        }

        source = attrs["source_configuration"]
        if config.image_repository_type == "ECR_PUBLIC":
            source["auto_deployments_enabled"] = False
        elif config.access_role_arn:
            source["authentication_configuration"] = {
                "access_role_arn": Expr("var.access_role_arn")
            }
        if config.instance_role_arn:
            attrs["instance_configuration"] = {
                "instance_role_arn": Expr("var.instance_role_arn")
            }
        if config._inject_runtime_secrets:
            attrs["depends_on"] = Expr("[aws_iam_role_policy.runtime_secrets]")
        return self._r.render_resource("aws_apprunner_service", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an App Runner service."""
        config = get_typed_config(instance, AppRunnerConfig)

        parts = [
            self._r.render_variable(
                "service_name", "string", "Name of the App Runner service"
            ),
            self._r.render_variable(
                "image_identifier",
                "string",
                "Container image identifier for the App Runner service",
            ),
        ]
        parts.append(
            self._r.render_variable(
                "runtime_environment_secrets",
                "map(string)",
                "External runtime secret ARNs",
                default=Expr(json.dumps(config.runtime_environment_secrets)),
            )
        )
        for name in ("image_repository_type", "access_role_arn", "instance_role_arn"):
            value = getattr(config, name)
            if value is not None:
                parts.append(
                    self._r.render_variable(
                        name, "string", name.replace("_", " "), default=value
                    )
                )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an App Runner service."""
        parts = [
            self._r.render_output(
                "service_arn",
                f"aws_apprunner_service.{instance.name}.arn",
                "ARN of the App Runner service",
            ),
            self._r.render_output(
                "service_url",
                f"aws_apprunner_service.{instance.name}.service_url",
                "URL of the App Runner service",
            ),
        ]
        return "\n".join(parts)
