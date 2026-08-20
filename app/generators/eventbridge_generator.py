"""EventBridge generator — produces HCL for event buses and rules."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.eventbridge_config import EventBridgeConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> EventBridgeConfig:
    return instance.config  # type: ignore[return-value]


class EventBridgeGenerator:
    """Generates Terraform files for EventBridge rules and their optional bus."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate the rule, plus a custom event bus when one is configured."""
        config = _resolve_config(instance)
        parts: list[str] = []

        if config.bus_name is not None:
            parts.append(
                self._r.render_resource(
                    "aws_cloudwatch_event_bus",
                    f"{instance.name}_bus",
                    {"name": Expr("var.bus_name")},
                )
            )

        attrs: dict = {"name": Expr("var.rule_name")}
        if config.bus_name is not None:
            attrs["event_bus_name"] = Expr(
                f"aws_cloudwatch_event_bus.{instance.name}_bus.name"
            )
        if config.description is not None:
            attrs["description"] = Expr("var.description")
        if config.event_pattern is not None:
            attrs["event_pattern"] = Expr("var.event_pattern")
        if config.schedule_expression is not None:
            attrs["schedule_expression"] = Expr("var.schedule_expression")
        if config.state is not None:
            attrs["state"] = Expr("var.state")
        if config.tags is not None:
            attrs["tags"] = Expr("var.tags")

        parts.append(
            self._r.render_resource("aws_cloudwatch_event_rule", instance.name, attrs)
        )
        return "\n".join(parts)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an EventBridge instance."""
        config = _resolve_config(instance)
        parts = [
            self._r.render_variable(
                "rule_name",
                "string",
                "Name of the EventBridge rule",
                default=config.rule_name or instance.name,
            )
        ]
        optional = [
            ("bus_name", "string", "Name of the custom event bus", config.bus_name),
            ("description", "string", "Description of the rule", config.description),
            ("event_pattern", "string", "JSON event pattern", config.event_pattern),
            (
                "schedule_expression",
                "string",
                "Schedule the rule fires on",
                config.schedule_expression,
            ),
            ("state", "string", "Whether the rule is enabled", config.state),
        ]
        for name, tf_type, description, value in optional:
            if value is not None:
                parts.append(
                    self._r.render_variable(name, tf_type, description, default=value)
                )
        if config.tags is not None:
            parts.append(
                self._r.render_variable("tags", "map(string)", "Tags for the rule")
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an EventBridge instance."""
        parts = [
            self._r.render_output(
                "rule_arn",
                f"aws_cloudwatch_event_rule.{instance.name}.arn",
                "ARN of the EventBridge rule",
            ),
            self._r.render_output(
                "rule_name",
                f"aws_cloudwatch_event_rule.{instance.name}.name",
                "Name of the EventBridge rule",
            ),
        ]
        return "\n".join(parts)
