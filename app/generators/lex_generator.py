from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.lex_config import LexConfig
from app.models.ir_models import ResourceInstanceIR


class LexGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, LexConfig)
        return self._r.render_resource(
            "aws_lexv2models_bot",
            instance.name,
            {
                "name": Expr("var.bot_name"),
                "role_arn": Expr("var.role_arn"),
                "idle_session_ttl_in_seconds": Expr("var.idle_session_ttl_in_seconds"),
                "data_privacy": {"child_directed": Expr("var.child_directed")},
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, LexConfig)
        fields = [
            ("bot_name", "string", "Bot name"),
            ("role_arn", "string", "Lex role ARN"),
            ("idle_session_ttl_in_seconds", "number", "Idle session timeout"),
            ("child_directed", "bool", "Whether the bot is child directed"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_lexv2models_bot.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("bot_id", f"{ref}.id", "Bot ID"),
            ]
        )
