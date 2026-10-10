from app.generators.ecs_logs import RESERVED_CONTAINERS
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.ecr_ecs import (
    CONTAINER_PATTERN,
    IMAGE_VERSION_PATTERN,
    PRIVATE_ECR_PATTERN,
    REPOSITORY_PATTERN,
)


def registry_image_preconditions() -> list[dict]:
    reserved = HCLRenderer().render_expression(list(RESERVED_CONTAINERS))
    return [
        {
            "condition": Expr(
                "length(var.registry_images) > 0 && length(distinct([for container in jsondecode(var.container_definitions) : container.name])) == length(jsondecode(var.container_definitions)) && alltrue([for name in keys(var.registry_images) : contains([for container in jsondecode(var.container_definitions) : container.name], name)])"
            ),
            "error_message": "Managed images require uniquely named application containers and every selected container in container_definitions.",
        },
        {
            "condition": Expr(
                f'alltrue([for container, binding in var.registry_images : can(regex("{CONTAINER_PATTERN}", container)) && !contains({reserved}, container) && can(regex("{IMAGE_VERSION_PATTERN}", binding.image_version)) && can(regex("{REPOSITORY_PATTERN}", binding.name)) && length(binding.name) >= 2 && length(binding.name) <= 256])'
            ),
            "error_message": "Use an application container name, valid private repository name, and literal image tag or sha256 digest.",
        },
        {
            "condition": Expr(
                'alltrue([for binding in values(var.registry_images) : binding.arn == "arn:${data.aws_partition.registry_images.partition}:ecr:${data.aws_region.registry_images.region}:${data.aws_caller_identity.registry_images.account_id}:repository/${binding.name}" && binding.url == "${data.aws_caller_identity.registry_images.account_id}.dkr.ecr.${data.aws_region.registry_images.region}.${data.aws_partition.registry_images.dns_suffix}/${binding.name}"])'
            ),
            "error_message": "Managed repositories must have matching native ARN, name, and URL in the task's partition, Region, and account.",
        },
        {
            "condition": Expr(
                "alltrue([for container in jsondecode(var.container_definitions) : try(container.repositoryCredentials, null) == null || try(length(keys(container.repositoryCredentials)) == 0, false) if contains(keys(var.registry_images), container.name)])"
            ),
            "error_message": "Remove external registry credentials from each container connected to ECR.",
        },
        {
            "condition": Expr(
                f'alltrue([for container in jsondecode(var.container_definitions) : contains(keys(var.registry_images), container.name) || !can(regex("{PRIVATE_ECR_PATTERN}", container.image))])'
            ),
            "error_message": "Connect every application container using a private ECR image so pull permissions remain scoped.",
        },
        {
            "condition": Expr(
                'var.ecs_launch_type == "FARGATE" && length(var.subnet_ids) > 0 && length(var.security_group_ids) > 0'
            ),
            "error_message": "Managed images require modeled Linux Fargate tasks and subnet/security-group placement.",
        },
    ]


def add_registry_image_attributes(attrs: dict, name: str) -> None:
    containers = attrs["container_definitions"]
    attrs["container_definitions"] = Expr(
        f'jsonencode([for container in jsondecode({containers}) : merge(container, {{ for name, image in local.registry_images : "image" => image if name == container.name }})])'
    )
    attrs["execution_role_arn"] = Expr(f"aws_iam_role.{name}_role.arn")
    lifecycle = attrs.setdefault("lifecycle", {})
    existing = lifecycle.get("precondition", [])
    lifecycle["precondition"] = (
        existing if isinstance(existing, list) else [existing]
    ) + registry_image_preconditions()


def render_registry_image_resources(renderer: HCLRenderer, name: str) -> str:
    result = """data "aws_partition" "registry_images" {}
data "aws_region" "registry_images" {}
data "aws_caller_identity" "registry_images" {}

locals {
  registry_images = { for container, binding in var.registry_images : container => "${binding.url}${startswith(binding.image_version, "sha256:") ? "@" : ":"}${binding.image_version}" }
}
"""
    return result + renderer.render_resource(
        "aws_iam_role_policy",
        "registry_images",
        {
            "name": "registry-images",
            "role": Expr(f"aws_iam_role.{name}_role.id"),
            "policy": Expr(
                'jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"], Resource = sort(distinct([for binding in values(var.registry_images) : binding.arn])) }] })'
            ),
        },
    )
