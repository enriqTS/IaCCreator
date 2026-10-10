from app.generators.hcl_renderer import Expr


def image_reference(binding: str) -> str:
    return f'"${{{binding}.url}}${{startswith({binding}.image_version, "sha256:") ? "@" : ":"}}${{{binding}.image_version}}"'


def repository_identity_condition() -> Expr:
    return Expr(
        'alltrue([for binding in values(var.registry_images) : binding.arn == "arn:${data.aws_partition.registry_images.partition}:ecr:${data.aws_region.registry_images.region}:${data.aws_caller_identity.registry_images.account_id}:repository/${binding.name}" && binding.url == "${data.aws_caller_identity.registry_images.account_id}.dkr.ecr.${data.aws_region.registry_images.region}.${data.aws_partition.registry_images.dns_suffix}/${binding.name}"])'
    )


def pull_policy(resources: str, *, authorization: bool = False) -> Expr:
    token = (
        '{ Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" }, '
        if authorization
        else ""
    )
    return Expr(
        'jsonencode({ Version = "2012-10-17", Statement = ['
        + token
        + '{ Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"], Resource = '
        + resources
        + " }] })"
    )
