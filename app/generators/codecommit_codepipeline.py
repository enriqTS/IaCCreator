from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.git_reference import GIT_REFERENCE_PATTERN
from app.models.iam_role import ROLE_ARN_PATTERN


def pipeline_source_preconditions() -> list[dict]:
    conditions = [
        (
            f'can(regex("{ROLE_ARN_PATTERN}", var.role_arn)) && try(split(":", var.role_arn)[1], "") == data.aws_partition.repository_source.partition && try(split(":", var.role_arn)[4], "") == data.aws_caller_identity.repository_source.account_id',
            "Repository sourcing requires a pipeline role in the deployment account and partition.",
        ),
        (
            'can(regex("^[A-Za-z0-9_.-]{1,100}$", var.repository_source.name)) && var.repository_source.arn == format("arn:%s:codecommit:%s:%s:%s", data.aws_partition.repository_source.partition, data.aws_region.repository_source.region, data.aws_caller_identity.repository_source.account_id, var.repository_source.name)',
            "The repository ARN must match its native name, deployment account, partition, and Region.",
        ),
        (
            f'can(regex("{GIT_REFERENCE_PATTERN}", var.repository_source.branch_name)) && !strcontains(var.repository_source.branch_name, "..") && !strcontains(var.repository_source.branch_name, "//") && !endswith(var.repository_source.branch_name, ".") && !endswith(var.repository_source.branch_name, "/") && alltrue([for part in split("/", var.repository_source.branch_name) : !startswith(part, ".") && !endswith(part, ".lock")])',
            "Select a literal ASCII Git branch without invalid ref components.",
        ),
        (
            'try(length(local.repository_stages) >= 2 && local.repository_stages[0].name == var.repository_source.stage_name && length([for stage in local.repository_stages : stage if stage.name == var.repository_source.stage_name]) == 1 && alltrue([for action in local.repository_stages[0].actions : action.category == "Source"]), false)',
            "The selected stage must remain the unique first source stage in a pipeline with at least two stages.",
        ),
        (
            'try(local.repository_action.category == "Source" && local.repository_action.owner == "AWS" && local.repository_action.provider == "CodeCommit" && local.repository_action.version == "1" && try(local.repository_action.role_arn, null) == null && try(local.repository_action.region, null) == null, false)',
            "The selected action must remain an AWS CodeCommit version 1 source without role or Region overrides.",
        ),
        (
            'try(length(local.repository_action.input_artifacts) == 0 && length(local.repository_action.output_artifacts) == 1 && can(regex("^[A-Za-z0-9_-]{1,100}$", local.repository_action.output_artifacts[0])) && length([for output in flatten([for stage in local.repository_stages : [for action in stage.actions : action.output_artifacts]]) : output if output == local.repository_action.output_artifacts[0]]) == 1, false)',
            "The selected source requires no input artifacts and one valid output artifact with a single producer.",
        ),
        (
            'try(lookup(local.repository_action.configuration, "OutputArtifactFormat", "CODE_ZIP") == "CODE_ZIP" && alltrue([for key in keys(local.repository_action.configuration) : contains(["RepositoryName", "BranchName", "PollForSourceChanges", "OutputArtifactFormat"], key)]), false)',
            "Only ZIP CodeCommit source configuration is supported by this connection.",
        ),
        (
            "try(length(trimspace(var.artifact_bucket_name)) > 0, false)",
            "A connected repository source requires a nonempty artifact store.",
        ),
    ]
    return [
        {"condition": Expr(condition), "error_message": message}
        for condition, message in conditions
    ]


def add_pipeline_source_attributes(attrs: dict) -> None:
    action = attrs['dynamic "stage"']["content"]['dynamic "action"']["content"]
    action["configuration"] = Expr(
        'stage.value.name == var.repository_source.stage_name && action.value.name == var.repository_source.action_name ? tomap({ RepositoryName = var.repository_source.name, BranchName = var.repository_source.branch_name, PollForSourceChanges = "false", OutputArtifactFormat = "CODE_ZIP" }) : action.value.configuration'
    )
    dependencies = str(attrs.get("depends_on", "[]"))[1:-1]
    attrs["depends_on"] = Expr(
        f"[{dependencies}{', ' if dependencies else ''}aws_iam_role_policy.repository_source]"
    )
    attrs.setdefault("lifecycle", {}).setdefault("precondition", []).extend(
        pipeline_source_preconditions()
    )


def pipeline_source_policy_preconditions() -> list[dict]:
    return [
        *pipeline_source_preconditions(),
        {
            "condition": Expr(
                "data.aws_iam_role.repository_source.arn == var.role_arn"
            ),
            "error_message": "The resolved pipeline-role ARN must match exactly, including its path.",
        },
    ]


def render_pipeline_source_resources(renderer: HCLRenderer) -> str:
    identity = "\n".join(
        f'data "{kind}" "repository_source" {{}}'
        for kind in ("aws_partition", "aws_region", "aws_caller_identity")
    )
    role = '\ndata "aws_iam_role" "repository_source" {\n  name = element(reverse(split("/", var.role_arn)), 0)\n}\n'
    locals_block = (
        "\nlocals {\n"
        "  repository_stages = try(jsondecode(var.stages_json), [])\n"
        "  repository_action = try(one([for action in local.repository_stages[0].actions : action if action.name == var.repository_source.action_name]), null)\n"
        "}\n\n"
    )
    policy = renderer.render_resource(
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
                            "Action": [
                                "codecommit:CancelUploadArchive",
                                "codecommit:GetBranch",
                                "codecommit:GetCommit",
                                "codecommit:GetRepository",
                                "codecommit:GetUploadArchiveStatus",
                                "codecommit:UploadArchive",
                            ],
                            "Resource": Expr("var.repository_source.arn"),
                        }
                    ],
                }
            ),
            "lifecycle": {"precondition": pipeline_source_policy_preconditions()},
        },
    )
    return identity + role + locals_block + policy
