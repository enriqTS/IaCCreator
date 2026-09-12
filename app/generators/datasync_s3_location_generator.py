"""Generate standalone S3 transfer locations for DataSync tasks."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.datasync_s3_location_config import DataSyncS3LocationConfig
from app.models.ir_models import ResourceInstanceIR


class DataSyncS3LocationGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, DataSyncS3LocationConfig)
        attrs = {
            "s3_bucket_arn": Expr("var.s3_bucket_arn"),
            "subdirectory": Expr("var.subdirectory"),
            "s3_config": {"bucket_access_role_arn": Expr("var.bucket_access_role_arn")},
        }
        if config._managed_bucket:
            attrs["depends_on"] = Expr("[aws_iam_role_policy.location_access]")
        return self._r.render_resource("aws_datasync_location_s3", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        return "\n".join(
            self._r.render_variable(name, "string", description)
            for name, description in [
                ("s3_bucket_arn", "S3 bucket ARN"),
                ("subdirectory", "S3 transfer path"),
                ("bucket_access_role_arn", "External DataSync access role"),
            ]
        )

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        return self._r.render_output(
            "location_arn",
            f"aws_datasync_location_s3.{instance.name}.arn",
            "DataSync location ARN",
        )
