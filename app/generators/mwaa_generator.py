"""Terraform generator for Amazon MWAA environments."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.mwaa_config import MwaaConfig
from app.models.ir_models import ResourceInstanceIR


class MwaaGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, MwaaConfig)
        attrs = {
            "name": instance.name,
            "execution_role_arn": Expr("var.execution_role_arn"),
            "source_bucket_arn": Expr("var.source_bucket_arn"),
            "dag_s3_path": Expr("var.dag_s3_path"),
            "environment_class": Expr("var.environment_class"),
            "max_workers": Expr("var.max_workers"),
            "min_workers": Expr("var.min_workers"),
            "webserver_access_mode": Expr("var.webserver_access_mode"),
            "network_configuration": [
                {
                    "security_group_ids": Expr("var.security_group_ids"),
                    "subnet_ids": Expr("var.subnet_ids"),
                }
            ],
        }
        if config.airflow_version is not None:
            attrs["airflow_version"] = Expr("var.airflow_version")
        return self._r.render_resource("aws_mwaa_environment", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, MwaaConfig)
        fields = [
            ("execution_role_arn", "string", "MWAA execution role ARN"),
            ("source_bucket_arn", "string", "Workflow source bucket ARN"),
            ("dag_s3_path", "string", "DAG directory path"),
            ("subnet_ids", "list(string)", "Private subnet IDs"),
            ("security_group_ids", "list(string)", "Environment security group IDs"),
            ("environment_class", "string", "MWAA environment class"),
            ("max_workers", "number", "Maximum worker count"),
            ("min_workers", "number", "Minimum worker count"),
            ("webserver_access_mode", "string", "Web server access mode"),
        ]
        if config.airflow_version is not None:
            fields.append(("airflow_version", "string", "Apache Airflow version"))
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_mwaa_environment.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "environment_arn", f"{ref}.arn", "MWAA environment ARN"
                ),
                self._r.render_output(
                    "webserver_url", f"{ref}.webserver_url", "Airflow web server URL"
                ),
            ]
        )
