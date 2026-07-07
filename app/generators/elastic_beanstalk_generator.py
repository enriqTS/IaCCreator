"""Elastic Beanstalk service generator — produces HCL for Beanstalk application and environment resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.elastic_beanstalk_config import ElasticBeanstalkConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> ElasticBeanstalkConfig:
    """Resolve typed ElasticBeanstalkConfig, falling back to instance.config during migration."""
    if isinstance(instance.config, ElasticBeanstalkConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class ElasticBeanstalkGenerator:
    """Generates Terraform files for Elastic Beanstalk applications and environments."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_elastic_beanstalk_application and aws_elastic_beanstalk_environment."""
        config = _resolve_config(instance)

        # Beanstalk Application
        app_attrs: dict = {"name": "var.application_name"}
        result = self._r.render_resource(
            "aws_elastic_beanstalk_application", instance.name, app_attrs
        )

        # Beanstalk Environment
        env_attrs: dict = {
            "name": "var.environment_name",
            "application": f"aws_elastic_beanstalk_application.{instance.name}.name",
        }
        if config.eb_solution_stack_name is not None:
            env_attrs["solution_stack_name"] = "var.eb_solution_stack_name"
        if config.eb_tier is not None:
            env_attrs["tier"] = "var.eb_tier"

        result += "\n" + self._r.render_resource(
            "aws_elastic_beanstalk_environment", f"{instance.name}_env", env_attrs
        )

        return result

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an Elastic Beanstalk instance."""
        config = _resolve_config(instance)

        parts = [
            self._r.render_variable(
                "application_name",
                "string",
                "Name of the Elastic Beanstalk application",
            ),
            self._r.render_variable(
                "environment_name",
                "string",
                "Name of the Elastic Beanstalk environment",
            ),
        ]
        if config.eb_solution_stack_name is not None:
            parts.append(
                self._r.render_variable(
                    "eb_solution_stack_name",
                    "string",
                    "Solution stack name for the Beanstalk environment",
                    default=config.eb_solution_stack_name,
                )
            )
        if config.eb_tier is not None:
            parts.append(
                self._r.render_variable(
                    "eb_tier",
                    "string",
                    "Tier for the Beanstalk environment (WebServer or Worker)",
                    default=config.eb_tier,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an Elastic Beanstalk instance."""
        parts = [
            self._r.render_output(
                "application_name",
                f"aws_elastic_beanstalk_application.{instance.name}.name",
                "Name of the Elastic Beanstalk application",
            ),
            self._r.render_output(
                "environment_endpoint",
                f"aws_elastic_beanstalk_environment.{instance.name}_env.endpoint_url",
                "Endpoint URL of the Elastic Beanstalk environment",
            ),
        ]
        return "\n".join(parts)
