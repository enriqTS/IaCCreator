"""MSK service generator — produces HCL for aws_msk_cluster resources."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.msk_config import MSK_IAM_VERSION_PATTERN, MskConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> MskConfig:
    """Resolve typed MskConfig, falling back to instance.config during migration."""
    return get_typed_config(instance, MskConfig)


class MSKGenerator:
    """Generates Terraform files for MSK clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_msk_cluster resource."""
        config = _resolve_config(instance)
        attrs: dict = {"cluster_name": Expr("var.cluster_name")}
        if config.kafka_version is not None:
            attrs["kafka_version"] = Expr("var.kafka_version")
        if config.number_of_broker_nodes is not None:
            attrs["number_of_broker_nodes"] = Expr("var.number_of_broker_nodes")
        attrs["broker_node_group_info"] = {
            "instance_type": Expr("var.broker_instance_type"),
            "client_subnets": Expr("var.subnet_ids"),
            "security_groups": Expr("var.security_group_ids"),
        }
        if config._iam_client_access:
            attrs["client_authentication"] = {
                "sasl": {"iam": True},
                "unauthenticated": False,
            }
            attrs["encryption_info"] = {
                "encryption_in_transit": {"client_broker": "TLS", "in_cluster": True}
            }
            pattern = self._r.render_expression(MSK_IAM_VERSION_PATTERN)
            message = "MSK IAM clients require Kafka 2.7.1 or newer."
            attrs["lifecycle"] = {
                "precondition": [
                    {
                        "condition": Expr(f"can(regex({pattern}, var.kafka_version))"),
                        "error_message": message,
                    },
                    {
                        "condition": Expr(
                            "contains([2, 3], length(var.subnet_ids)) && length(distinct(var.subnet_ids)) == length(var.subnet_ids) && length(var.security_group_ids) > 0 && var.number_of_broker_nodes > 0 && var.number_of_broker_nodes % max(1, length(var.subnet_ids)) == 0"
                        ),
                        "error_message": "MSK requires two or three distinct broker subnets, security groups, and a positive broker count divisible by the subnet count.",
                    },
                ],
                "postcondition": {
                    "condition": Expr(f"can(regex({pattern}, self.kafka_version))"),
                    "error_message": message,
                },
            }

        return self._r.render_resource("aws_msk_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an MSK cluster."""
        config = _resolve_config(instance)
        parts = [
            self._r.render_variable(
                "cluster_name", "string", "Name of the MSK cluster"
            ),
        ]
        for name, kind, description in (
            ("broker_instance_type", "string", "MSK broker instance type"),
            ("subnet_ids", "list(string)", "Broker subnets"),
            ("security_group_ids", "list(string)", "Broker security groups"),
        ):
            parts.append(
                self._r.render_variable(
                    name, kind, description, default=getattr(config, name)
                )
            )
        if config.kafka_version is not None:
            parts.append(
                self._r.render_variable(
                    "kafka_version",
                    "string",
                    "Kafka version for the MSK cluster",
                    default=config.kafka_version,
                )
            )
        if config.number_of_broker_nodes is not None:
            parts.append(
                self._r.render_variable(
                    "number_of_broker_nodes",
                    "number",
                    "Number of broker nodes in the MSK cluster",
                    default=config.number_of_broker_nodes,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an MSK cluster."""
        parts = [
            self._r.render_output(
                "cluster_arn",
                f"aws_msk_cluster.{instance.name}.arn",
                "ARN of the MSK cluster",
            ),
            self._r.render_output(
                "bootstrap_brokers",
                f"aws_msk_cluster.{instance.name}.bootstrap_brokers",
                "Bootstrap brokers for the MSK cluster",
            ),
        ]
        return "\n".join(parts)
