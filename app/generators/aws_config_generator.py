from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.aws_config_config import AwsConfigConfig
from app.models.ir_models import ResourceInstanceIR


class AwsConfigGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, AwsConfigConfig)
        recorder = self._r.render_resource(
            "aws_config_configuration_recorder",
            instance.name,
            {
                "name": Expr("var.recorder_name"),
                "role_arn": Expr("var.role_arn"),
                "recording_group": {
                    "all_supported": Expr("var.all_supported"),
                    "include_global_resource_types": Expr(
                        "var.include_global_resource_types"
                    ),
                },
            },
        )
        channel = self._r.render_resource(
            "aws_config_delivery_channel",
            instance.name,
            {
                "name": Expr("var.recorder_name"),
                "s3_bucket_name": Expr("var.s3_bucket_name"),
                "depends_on": Expr(
                    f"[aws_config_configuration_recorder.{instance.name}]"
                ),
            },
        )
        status = self._r.render_resource(
            "aws_config_configuration_recorder_status",
            instance.name,
            {
                "name": Expr(f"aws_config_configuration_recorder.{instance.name}.name"),
                "is_enabled": True,
                "depends_on": Expr(f"[aws_config_delivery_channel.{instance.name}]"),
            },
        )
        return "\n".join([recorder, channel, status])

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, AwsConfigConfig)
        fields = [
            ("recorder_name", "string", "Configuration recorder name"),
            ("role_arn", "string", "AWS Config IAM role ARN"),
            ("s3_bucket_name", "string", "S3 delivery bucket name"),
            ("all_supported", "bool", "Record every supported resource type"),
            (
                "include_global_resource_types",
                "bool",
                "Include global resource types",
            ),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_config_configuration_recorder.{instance.name}"
        return self._r.render_output(
            "recorder_name", f"{ref}.name", "Configuration recorder name"
        )
