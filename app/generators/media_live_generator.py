from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.media_live_config import MediaLiveConfig
from app.models.ir_models import ResourceInstanceIR


class MediaLiveGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, MediaLiveConfig)
        rules = [
            {"cidr": Expr(f"var.allowed_cidrs[{index}]")}
            for index in range(len(config.allowed_cidrs))
        ]
        return self._r.render_resource(
            "aws_medialive_input_security_group",
            instance.name,
            {"whitelist_rules": rules, "tags": Expr("var.tags")},
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, MediaLiveConfig)
        fields = [
            ("allowed_cidrs", "list(string)", "Allowed video source CIDRs"),
            ("tags", "map(string)", "Input security group tags"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_medialive_input_security_group.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "security_group_id",
                    f"{ref}.id",
                    "MediaLive input security group ID",
                ),
                self._r.render_output(
                    "security_group_arn",
                    f"{ref}.arn",
                    "MediaLive input security group ARN",
                ),
            ]
        )
