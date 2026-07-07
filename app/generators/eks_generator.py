"""EKS service generator — produces HCL for aws_eks_cluster resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class EKSGenerator:
    """Generates Terraform files for EKS clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_eks_cluster resource."""
        vpc_config: dict = {"subnet_ids": "var.subnet_ids"}
        if instance.config.eks_endpoint_public_access is not None:
            vpc_config["endpoint_public_access"] = "var.eks_endpoint_public_access"

        attrs: dict = {
            "name": "var.cluster_name",
            "role_arn": "var.cluster_role_arn",
            "vpc_config": vpc_config,
        }
        if instance.config.eks_version is not None:
            attrs["version"] = "var.eks_version"

        return self._r.render_resource("aws_eks_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an EKS cluster."""
        parts = [
            self._r.render_variable(
                "cluster_name", "string", "Name of the EKS cluster"
            ),
            self._r.render_variable(
                "cluster_role_arn", "string", "ARN of the IAM role for the EKS cluster"
            ),
            self._r.render_variable(
                "subnet_ids",
                "list(string)",
                "List of subnet IDs for the EKS cluster VPC config",
            ),
        ]
        if instance.config.eks_version is not None:
            parts.append(
                self._r.render_variable(
                    "eks_version",
                    "string",
                    "Kubernetes version for the EKS cluster",
                    default=instance.config.eks_version,
                )
            )
        if instance.config.eks_endpoint_public_access is not None:
            parts.append(
                self._r.render_variable(
                    "eks_endpoint_public_access",
                    "bool",
                    "Whether the EKS cluster endpoint is publicly accessible",
                    default=instance.config.eks_endpoint_public_access,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an EKS cluster."""
        parts = [
            self._r.render_output(
                "cluster_arn",
                f"aws_eks_cluster.{instance.name}.arn",
                "ARN of the EKS cluster",
            ),
            self._r.render_output(
                "cluster_endpoint",
                f"aws_eks_cluster.{instance.name}.endpoint",
                "Endpoint URL of the EKS cluster",
            ),
            self._r.render_output(
                "cluster_name",
                f"aws_eks_cluster.{instance.name}.name",
                "Name of the EKS cluster",
            ),
        ]
        return "\n".join(parts)
