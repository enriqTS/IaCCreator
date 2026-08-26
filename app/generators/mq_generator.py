"""Terraform generator for Amazon MQ brokers."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.mq_config import MqConfig
from app.models.ir_models import ResourceInstanceIR


class MqGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, MqConfig)
        return self._r.render_resource(
            "aws_mq_broker",
            instance.name,
            {
                "broker_name": instance.name,
                "engine_type": "ActiveMQ",
                "engine_version": Expr("var.engine_version"),
                "host_instance_type": Expr("var.host_instance_type"),
                "deployment_mode": Expr("var.deployment_mode"),
                "subnet_ids": Expr("var.subnet_ids"),
                "security_groups": Expr("var.security_group_ids"),
                "publicly_accessible": Expr("var.publicly_accessible"),
                "auto_minor_version_upgrade": Expr("var.auto_minor_version_upgrade"),
                "user": [
                    {"username": Expr("var.username"), "password": Expr("var.password")}
                ],
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, MqConfig)
        fields = [
            ("engine_version", "string", "ActiveMQ engine version"),
            ("host_instance_type", "string", "Broker instance type"),
            ("deployment_mode", "string", "Broker deployment mode"),
            ("subnet_ids", "list(string)", "Broker subnet IDs"),
            ("security_group_ids", "list(string)", "Broker security group IDs"),
            ("publicly_accessible", "bool", "Allow public broker access"),
            ("username", "string", "Initial broker username"),
            ("password", "string", "Initial broker password"),
            ("auto_minor_version_upgrade", "bool", "Install minor engine upgrades"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_mq_broker.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("broker_id", f"{ref}.id", "Broker ID"),
                self._r.render_output("broker_arn", f"{ref}.arn", "Broker ARN"),
                self._r.render_output(
                    "broker_instances", f"{ref}.instances", "Broker endpoints"
                ),
            ]
        )
