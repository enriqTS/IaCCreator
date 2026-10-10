from app.generators.ecr_eks_manifests import image_locals
from app.generators.ecr_images import pull_policy, repository_identity_condition
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.ecr_eks import (
    DEPLOYMENT_PATTERN,
    KUBERNETES_LABEL_PATTERN,
)
from app.models.ecr_image import IMAGE_VERSION_PATTERN, REPOSITORY_PATTERN
from app.models.iam_role import ROLE_ARN_PATTERN


def eks_image_preconditions(cluster: str) -> list[dict]:
    conditions = [
        (
            repository_identity_condition(),
            "Repository ARN, name, and URL must match the cluster's account, partition, and Region.",
        ),
        (
            f'length(var.registry_images) > 0 && alltrue([for binding in values(var.registry_images) : can(regex("{REPOSITORY_PATTERN}", binding.name)) && length(binding.name) >= 2 && length(binding.name) <= 256 && can(regex("{IMAGE_VERSION_PATTERN}", binding.image_version))])',
            "Use native private repository names and literal image tags or sha256 digests.",
        ),
        (
            f'alltrue([for binding in values(var.registry_images) : can(regex("{KUBERNETES_LABEL_PATTERN}", binding.namespace)) && can(regex("{KUBERNETES_LABEL_PATTERN}", binding.container_name)) && can(regex("{DEPLOYMENT_PATTERN}", binding.deployment_name)) && length(binding.deployment_name) <= 253 && alltrue([for part in split(".", binding.deployment_name) : can(regex("{KUBERNETES_LABEL_PATTERN}", part))])])',
            "Use bounded Kubernetes namespace, Deployment, and application-container names.",
        ),
        (
            "alltrue([for bindings in values(local.registry_containers) : length(distinct([for binding in bindings : binding.image])) == 1])",
            "Every Deployment container must use one consistent repository image across all pull roles.",
        ),
        (
            'alltrue([for types in values(local.registry_role_types) : length(distinct(types)) == 1 && alltrue([for role_type in types : contains(["node", "fargate"], role_type)])])',
            "Each external image pull role must have one explicit EC2 node or Fargate compute type.",
        ),
        (
            f'alltrue([for binding in values(var.registry_images) : can(regex("{ROLE_ARN_PATTERN}", binding.pull_role_arn)) && try(split(":", binding.pull_role_arn)[1], "") == data.aws_partition.registry_images.partition && try(split(":", binding.pull_role_arn)[4], "") == data.aws_caller_identity.registry_images.account_id && binding.pull_role_arn != var.cluster_role_arn])',
            "Use a worker or Fargate pod execution role in the deployment account and partition, distinct from the cluster role.",
        ),
        (
            f'{cluster}.arn == "arn:${{data.aws_partition.registry_images.partition}}:eks:${{data.aws_region.registry_images.region}}:${{data.aws_caller_identity.registry_images.account_id}}:cluster/${{{cluster}.name}}"',
            "Image patches must target the native cluster in the deployment account, partition, and Region.",
        ),
    ]
    return [
        {"condition": Expr(condition), "error_message": message}
        for condition, message in conditions
    ]


def pull_role_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                "data.aws_iam_role.registry_images[each.key].arn == each.value[0]"
            ),
            "error_message": "The resolved image pull role must match its full ARN, including path.",
        },
        {
            "condition": Expr(
                'anytrue([for statement in try(jsondecode(data.aws_iam_role.registry_images[each.key].assume_role_policy).Statement[*], []) : try(statement.Effect == "Allow" && contains(flatten([statement.Action]), "sts:AssumeRole") && contains(flatten([statement.Principal.Service]), lookup({ node = "ec2.amazonaws.com", fargate = "eks-fargate-pods.amazonaws.com" }, local.registry_role_types[each.key][0], "invalid")), false)])'
            ),
            "error_message": "The existing role must explicitly allow sts:AssumeRole for its selected EC2 or EKS Fargate compute service.",
        },
    ]


def render_eks_image_resources(renderer: HCLRenderer, name: str) -> str:
    identity = "\n".join(
        f'data "{kind}" "registry_images" {{}}'
        for kind in ("aws_partition", "aws_region", "aws_caller_identity")
    )
    locals_body = (
        "\nlocals {\n"
        + "\n".join(f"  {key} = {value}" for key, value in image_locals().items())
        + "\n}\n"
    )
    role = """data "aws_iam_role" "registry_images" {
  for_each = local.registry_pull_roles
  name = element(reverse(split("/", each.value[0])), 0)
}
"""
    return (
        identity
        + locals_body
        + role
        + renderer.render_resource(
            "aws_iam_role_policy",
            "registry_images",
            {
                "for_each": Expr("local.registry_pull_roles"),
                "name_prefix": "ecr-eks-images-",
                "role": Expr("data.aws_iam_role.registry_images[each.key].name"),
                "policy": pull_policy(
                    "sort(distinct([for binding in values(var.registry_images) : binding.arn if binding.pull_role_arn == each.value[0]]))",
                    authorization=True,
                ),
                "lifecycle": {
                    "precondition": [
                        *eks_image_preconditions(f"aws_eks_cluster.{name}"),
                        *pull_role_preconditions(),
                    ]
                },
            },
        )
    )
