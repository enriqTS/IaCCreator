from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.iot_core_config import IotCoreConfig
from app.models.ir_models import ResourceInstanceIR


class IotCoreGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, IotCoreConfig)
        attrs: dict = {
            "name": Expr("var.thing_name"),
            "attributes": Expr("var.attributes"),
        }
        if config.thing_type_name:
            attrs["thing_type_name"] = Expr("var.thing_type_name")
        return self._r.render_resource("aws_iot_thing", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, IotCoreConfig)
        fields = [
            ("thing_name", "string", "IoT thing name"),
            ("thing_type_name", "string", "Optional IoT thing type"),
            ("attributes", "map(string)", "Thing registry attributes"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_iot_thing.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("thing_arn", f"{ref}.arn", "IoT thing ARN"),
                self._r.render_output("thing_name", f"{ref}.name", "IoT thing name"),
                self._r.render_output(
                    "client_id", f"{ref}.default_client_id", "Default MQTT client ID"
                ),
            ]
        )
