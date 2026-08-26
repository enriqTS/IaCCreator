from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.cloudtrail_config import CloudTrailConfig
from app.models.ir_models import ResourceInstanceIR


class CloudtrailGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, CloudTrailConfig)
        return self._r.render_resource(
            "aws_cloudtrail",
            instance.name,
            {
                "name": Expr("var.trail_name"),
                "s3_bucket_name": Expr("var.s3_bucket_name"),
                "include_global_service_events": Expr(
                    "var.include_global_service_events"
                ),
                "is_multi_region_trail": Expr("var.is_multi_region_trail"),
                "enable_log_file_validation": Expr("var.enable_log_file_validation"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, CloudTrailConfig)
        fields = [
            ("trail_name", "string", "CloudTrail trail name"),
            ("s3_bucket_name", "string", "S3 delivery bucket name"),
            ("include_global_service_events", "bool", "Include global service events"),
            ("is_multi_region_trail", "bool", "Record every region"),
            ("enable_log_file_validation", "bool", "Enable log validation"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_cloudtrail.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("trail_arn", f"{ref}.arn", "Trail ARN"),
                self._r.render_output("trail_name", f"{ref}.name", "Trail name"),
            ]
        )
