from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.datasync_config import DataSyncConfig
from app.models.ir_models import ResourceInstanceIR


class DataSyncGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, DataSyncConfig)
        return self._r.render_resource(
            "aws_datasync_task",
            instance.name,
            {
                "name": Expr("var.task_name"),
                "source_location_arn": Expr("var.source_location_arn"),
                "destination_location_arn": Expr("var.destination_location_arn"),
                "options": {
                    "verify_mode": Expr("var.verify_mode"),
                    "overwrite_mode": Expr("var.overwrite_mode"),
                },
                "tags": Expr("var.tags"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, DataSyncConfig)
        fields = [
            ("task_name", "string", "DataSync task name"),
            ("source_location_arn", "string", "Source location ARN"),
            ("destination_location_arn", "string", "Destination location ARN"),
            ("verify_mode", "string", "Data verification mode"),
            ("overwrite_mode", "string", "Destination overwrite behavior"),
            ("tags", "map(string)", "Task tags"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_datasync_task.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("task_arn", f"{ref}.arn", "DataSync task ARN"),
                self._r.render_output("task_name", f"{ref}.name", "DataSync task name"),
            ]
        )
