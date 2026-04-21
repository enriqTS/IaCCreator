"""MSK service generator — produces HCL for aws_msk_cluster resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class MSKGenerator:
    """Generates Terraform files for MSK clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_msk_cluster resource."""
        attrs: dict = {"cluster_name": "var.cluster_name"}
        if instance.config.msk_kafka_version is not None:
            attrs["kafka_version"] = "var.kafka_version"
        if instance.config.msk_number_of_broker_nodes is not None:
            attrs["number_of_broker_nodes"] = "var.number_of_broker_nodes"

        return self._r.render_resource("aws_msk_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an MSK cluster."""
        parts = [
            self._r.render_variable("cluster_name", "string", "Name of the MSK cluster"),
        ]
        if instance.config.msk_kafka_version is not None:
            parts.append(self._r.render_variable(
                "kafka_version", "string", "Kafka version for the MSK cluster",
                default=instance.config.msk_kafka_version,
            ))
        if instance.config.msk_number_of_broker_nodes is not None:
            parts.append(self._r.render_variable(
                "number_of_broker_nodes", "number", "Number of broker nodes in the MSK cluster",
                default=instance.config.msk_number_of_broker_nodes,
            ))
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
