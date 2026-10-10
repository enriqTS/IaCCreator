"""Connection capabilities share one profile and deterministic policy dependencies."""

from app.generators.hcl_renderer import Expr
from app.models.input_models.ec2_config import Ec2Config

RUNTIME_POLICIES = {
    "_reads_runtime_secrets": "aws_iam_role_policy.runtime_secrets",
    "_mounts_efs": "aws_iam_role_policy.efs_mounts",
    "_managed_ssm": "aws_iam_role_policy_attachment.ssm_core",
}


def add_runtime_identity(attrs: dict, config: Ec2Config) -> None:
    policies = [
        policy
        for capability, policy in RUNTIME_POLICIES.items()
        if getattr(config, capability)
    ]
    if policies:
        attrs["iam_instance_profile"] = Expr(
            "aws_iam_instance_profile.runtime_secrets.name"
        )
        attrs["depends_on"] = Expr("[" + ", ".join(policies) + "]")
