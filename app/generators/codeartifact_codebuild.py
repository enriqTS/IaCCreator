from app.generators.codeartifact_buildspec import (
    package_buildspec_preconditions,
    render_package_buildspec_locals,
)
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.codeartifact_codebuild import (
    DOMAIN_PATTERN,
    REPOSITORY_PATTERN,
)
from app.models.iam_role import ROLE_ARN_PATTERN


def package_source_preconditions() -> list[dict]:
    conditions = [
        (
            f'can(regex("{ROLE_ARN_PATTERN}", var.service_role)) && try(split(":", var.service_role)[1], "") == data.aws_partition.package_source.partition && try(split(":", var.service_role)[4], "") == data.aws_caller_identity.package_source.account_id',
            "Package reads require a build service role in the deployment account and partition.",
        ),
        (
            f'can(regex("{DOMAIN_PATTERN}", var.package_source.domain_name)) && var.package_source.owner == data.aws_caller_identity.package_source.account_id && var.package_source.domain_arn == format("arn:%s:codeartifact:%s:%s:domain/%s", data.aws_partition.package_source.partition, data.aws_region.package_source.region, var.package_source.owner, var.package_source.domain_name)',
            "The native domain ARN/name/owner must match the deployment account, partition, and Region.",
        ),
        (
            f'can(regex("{REPOSITORY_PATTERN}", var.package_source.repository_name)) && var.package_source.repository_arn == format("arn:%s:codeartifact:%s:%s:repository/%s/%s", data.aws_partition.package_source.partition, data.aws_region.package_source.region, var.package_source.owner, var.package_source.domain_name, var.package_source.repository_name)',
            "The native repository ARN must belong to the connected domain, owner, partition, and Region.",
        ),
        (
            'contains(["npm", "pip"], var.package_source.tool)',
            "Package login supports only npm and pip.",
        ),
    ]
    return [
        {"condition": Expr(condition), "error_message": message}
        for condition, message in conditions
    ] + package_buildspec_preconditions()


def add_package_source_attributes(attrs: dict) -> None:
    attrs["source"]["buildspec"] = Expr("local.package_login_buildspec")
    dependencies = str(attrs.get("depends_on", "[]"))[1:-1]
    attrs["depends_on"] = Expr(
        f"[{dependencies}{', ' if dependencies else ''}aws_iam_role_policy.package_source]"
    )
    attrs.setdefault("lifecycle", {}).setdefault("precondition", []).extend(
        package_source_preconditions()
    )


def render_package_source_resources(renderer: HCLRenderer) -> str:
    identity = "\n".join(
        f'data "{kind}" "package_source" {{}}'
        for kind in ("aws_partition", "aws_region", "aws_caller_identity")
    )
    role = '\ndata "aws_iam_role" "package_source" {\n  name = element(reverse(split("/", var.service_role)), 0)\n}\n'
    statements = [
        {
            "Effect": "Allow",
            "Action": ["codeartifact:GetAuthorizationToken"],
            "Resource": Expr("var.package_source.domain_arn"),
        },
        {
            "Effect": "Allow",
            "Action": [
                "codeartifact:GetRepositoryEndpoint",
                "codeartifact:ReadFromRepository",
            ],
            "Resource": Expr("var.package_source.repository_arn"),
        },
        {
            "Effect": "Allow",
            "Action": ["sts:GetServiceBearerToken"],
            "Resource": "*",
            "Condition": {
                "StringEquals": {"sts:AWSServiceName": "codeartifact.amazonaws.com"}
            },
        },
    ]
    policy = renderer.render_resource(
        "aws_iam_role_policy",
        "package_source",
        {
            "name_prefix": "package-source-",
            "role": Expr("data.aws_iam_role.package_source.name"),
            "policy": renderer.render_json_policy(
                {"Version": "2012-10-17", "Statement": statements}, depth=2
            ),
            "lifecycle": {
                "precondition": [
                    *package_source_preconditions(),
                    {
                        "condition": Expr(
                            "data.aws_iam_role.package_source.arn == var.service_role"
                        ),
                        "error_message": "The resolved build service-role ARN must match exactly, including its path.",
                    },
                ]
            },
        },
    )
    return identity + role + render_package_buildspec_locals() + policy
