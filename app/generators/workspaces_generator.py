"""Terraform generator for Amazon WorkSpaces workspaces."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.workspaces_config import WorkSpacesConfig
from app.models.ir_models import ResourceInstanceIR


class WorkSpacesGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, WorkSpacesConfig)
        properties = {"running_mode": Expr("var.running_mode")}
        if config.running_mode == "AUTO_STOP":
            properties["running_mode_auto_stop_timeout_in_minutes"] = Expr(
                "var.running_mode_auto_stop_timeout_in_minutes"
            )
        attrs = {
            "directory_id": Expr("var.directory_id"),
            "bundle_id": Expr("var.bundle_id"),
            "user_name": Expr("var.user_name"),
            "root_volume_encryption_enabled": Expr(
                "var.root_volume_encryption_enabled"
            ),
            "user_volume_encryption_enabled": Expr(
                "var.user_volume_encryption_enabled"
            ),
            "workspace_properties": [properties],
        }
        if config.volume_encryption_key is not None:
            attrs["volume_encryption_key"] = Expr("var.volume_encryption_key")
        return self._r.render_resource("aws_workspaces_workspace", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, WorkSpacesConfig)
        fields = [
            ("directory_id", "string", "Directory Service directory ID"),
            ("bundle_id", "string", "WorkSpaces bundle ID"),
            ("user_name", "string", "Directory user name"),
            ("running_mode", "string", "Workspace running mode"),
            (
                "running_mode_auto_stop_timeout_in_minutes",
                "number",
                "Auto-stop timeout in minutes",
            ),
            ("root_volume_encryption_enabled", "bool", "Encrypt the root volume"),
            ("user_volume_encryption_enabled", "bool", "Encrypt the user volume"),
        ]
        if config.volume_encryption_key is not None:
            fields.append(
                ("volume_encryption_key", "string", "Volume encryption KMS key")
            )
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_workspaces_workspace.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("workspace_id", f"{ref}.id", "Workspace ID"),
                self._r.render_output(
                    "computer_name", f"{ref}.computer_name", "Workspace computer name"
                ),
                self._r.render_output(
                    "ip_address", f"{ref}.ip_address", "Workspace IP address"
                ),
            ]
        )
