from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.codecommit_codebuild import REVISION_PATTERN
from app.models.iam_role import ROLE_ARN_PATTERN


def repository_source_preconditions() -> list[dict]:
    conditions = [
        (
            f'can(regex("{ROLE_ARN_PATTERN}", var.service_role)) && try(split(":", var.service_role)[1], "") == data.aws_partition.repository_source.partition && try(split(":", var.service_role)[4], "") == data.aws_caller_identity.repository_source.account_id',
            "Repository checkout requires a service role in the deployment account and partition.",
        ),
        (
            'can(regex("^[A-Za-z0-9_.-]{1,100}$", var.repository_source.name)) && var.repository_source.arn == format("arn:%s:codecommit:%s:%s:%s", data.aws_partition.repository_source.partition, data.aws_region.repository_source.region, data.aws_caller_identity.repository_source.account_id, var.repository_source.name)',
            "The native repository ARN must match its name, deployment account, partition, and Region.",
        ),
        (
            'var.repository_source.clone_url == format("https://git-codecommit.%s.%s/v1/repos/%s", data.aws_region.repository_source.region, data.aws_partition.repository_source.dns_suffix, var.repository_source.name)',
            "The checkout location must be the connected repository's native HTTPS clone URL.",
        ),
        (
            'var.source_type == "CODECOMMIT"',
            "A connected repository owns the CODECOMMIT primary source; other source-type overrides are unsupported.",
        ),
        (
            f'can(regex("{REVISION_PATTERN}", var.repository_source.source_version)) && !strcontains(var.repository_source.source_version, "..") && !strcontains(var.repository_source.source_version, "//") && !endswith(var.repository_source.source_version, ".") && !endswith(var.repository_source.source_version, "/") && alltrue([for part in split("/", var.repository_source.source_version) : !startswith(part, ".") && !endswith(part, ".lock")])',
            "Select a literal ASCII Git branch, tag, or commit without invalid ref components.",
        ),
        (
            "var.repository_source.git_clone_depth >= 0 && var.repository_source.git_clone_depth <= 25 && floor(var.repository_source.git_clone_depth) == var.repository_source.git_clone_depth",
            "Clone depth must be an integer from 0 to 25; zero selects full history.",
        ),
    ]
    return [
        {"condition": Expr(condition), "error_message": message}
        for condition, message in conditions
    ]


def add_repository_source_attributes(attrs: dict) -> None:
    attrs["source"].update(
        {
            "type": Expr("var.source_type"),
            "location": Expr("var.repository_source.clone_url"),
            "git_clone_depth": Expr("var.repository_source.git_clone_depth"),
            "git_submodules_config": {"fetch_submodules": False},
            "insecure_ssl": False,
        }
    )
    attrs["source_version"] = Expr("var.repository_source.source_version")
    dependencies = str(attrs.get("depends_on", "[]"))[1:-1]
    attrs["depends_on"] = Expr(
        f"[{dependencies}{', ' if dependencies else ''}aws_iam_role_policy.repository_source]"
    )
    attrs.setdefault("lifecycle", {}).setdefault("precondition", []).extend(
        repository_source_preconditions()
    )


def render_repository_source_resources(renderer: HCLRenderer) -> str:
    identity = "\n".join(
        f'data "{kind}" "repository_source" {{}}'
        for kind in ("aws_partition", "aws_region", "aws_caller_identity")
    )
    role = '\ndata "aws_iam_role" "repository_source" {\n  name = element(reverse(split("/", var.service_role)), 0)\n}\n'
    return (
        identity
        + role
        + renderer.render_resource(
            "aws_iam_role_policy",
            "repository_source",
            {
                "name_prefix": "repository-source-",
                "role": Expr("data.aws_iam_role.repository_source.name"),
                "policy": renderer.render_json_policy(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": ["codecommit:GitPull"],
                                "Resource": Expr("var.repository_source.arn"),
                            }
                        ],
                    },
                    depth=2,
                ),
                "lifecycle": {
                    "precondition": [
                        *repository_source_preconditions(),
                        {
                            "condition": Expr(
                                "data.aws_iam_role.repository_source.arn == var.service_role"
                            ),
                            "error_message": "The resolved service-role ARN must match exactly, including its path.",
                        },
                    ]
                },
            },
        )
    )
