from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.managed_prometheus_config import ManagedPrometheusConfig
from app.models.ir_models import ResourceInstanceIR


class ManagedPrometheusGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, ManagedPrometheusConfig)
        attrs = {"alias": Expr("var.alias")}
        if config._managed_scraper:
            attrs["tags"] = Expr(self._r.render_expression({"AMPAgentlessScraper": ""}))
        return self._r.render_resource(
            "aws_prometheus_workspace",
            instance.name,
            attrs,
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, ManagedPrometheusConfig)
        fields = [
            ("alias", "string", "Workspace alias"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_prometheus_workspace.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("workspace_id", f"{ref}.id", "Workspace ID"),
                self._r.render_output("workspace_arn", f"{ref}.arn", "Workspace ARN"),
                self._r.render_output(
                    "prometheus_endpoint",
                    f"{ref}.prometheus_endpoint",
                    "Prometheus endpoint",
                ),
            ]
        )
