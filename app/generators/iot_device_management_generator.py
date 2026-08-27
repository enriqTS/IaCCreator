from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.iot_device_management_config import (
    IotDeviceManagementConfig,
)
from app.models.ir_models import ResourceInstanceIR


class IotDeviceManagementGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, IotDeviceManagementConfig)
        attrs: dict = {
            "name": Expr("var.thing_group_name"),
            "tags": Expr("var.tags"),
        }
        if config.parent_group_name:
            attrs["parent_group_name"] = Expr("var.parent_group_name")
        return self._r.render_resource("aws_iot_thing_group", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, IotDeviceManagementConfig)
        fields = [
            ("thing_group_name", "string", "IoT thing group name"),
            ("parent_group_name", "string", "Optional parent thing group name"),
            ("tags", "map(string)", "Thing group tags"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_iot_thing_group.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "thing_group_arn", f"{ref}.arn", "Thing group ARN"
                ),
                self._r.render_output(
                    "thing_group_name", f"{ref}.name", "Thing group name"
                ),
            ]
        )
