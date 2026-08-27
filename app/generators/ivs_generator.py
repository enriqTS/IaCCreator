from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.ivs_config import IvsConfig
from app.models.ir_models import ResourceInstanceIR


class IvsGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, IvsConfig)
        return self._r.render_resource(
            "aws_ivs_channel",
            instance.name,
            {
                "name": Expr("var.channel_name"),
                "type": Expr("var.channel_type"),
                "latency_mode": Expr("var.latency_mode"),
                "authorized": Expr("var.authorized"),
                "tags": Expr("var.tags"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, IvsConfig)
        fields = [
            ("channel_name", "string", "IVS channel name"),
            ("channel_type", "string", "IVS channel type"),
            ("latency_mode", "string", "Channel latency mode"),
            ("authorized", "bool", "Require playback authorization"),
            ("tags", "map(string)", "Channel tags"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_ivs_channel.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("channel_arn", f"{ref}.arn", "IVS channel ARN"),
                self._r.render_output(
                    "ingest_endpoint", f"{ref}.ingest_endpoint", "IVS ingest endpoint"
                ),
                self._r.render_output(
                    "playback_url", f"{ref}.playback_url", "IVS playback URL"
                ),
            ]
        )
