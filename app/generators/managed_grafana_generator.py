from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.managed_grafana_config import ManagedGrafanaConfig
from app.models.ir_models import ResourceInstanceIR


class ManagedGrafanaGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, ManagedGrafanaConfig)
        return self._r.render_resource(
            "aws_grafana_workspace",
            instance.name,
            {
                "name": Expr("var.workspace_name"),
                "account_access_type": Expr("var.account_access_type"),
                "authentication_providers": Expr("var.authentication_providers"),
                "permission_type": Expr("var.permission_type"),
                "data_sources": Expr("var.data_sources"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, ManagedGrafanaConfig)
        fields = [
            ("workspace_name", "string", "Workspace name"),
            ("account_access_type", "string", "Account access type"),
            ("authentication_providers", "list(string)", "Authentication providers"),
            ("permission_type", "string", "Permission type"),
            ("data_sources", "list(string)", "AWS data sources"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_grafana_workspace.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("workspace_id", f"{ref}.id", "Workspace ID"),
                self._r.render_output(
                    "workspace_endpoint", f"{ref}.endpoint", "Workspace endpoint"
                ),
            ]
        )
