"""Native identities, pinned versions, and daily schedules bound association targets."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.connection_configs.ssm_ec2 import DOCUMENT_NAME_PATTERN


def association_preconditions(document: str) -> list[dict]:
    return [
        {
            "condition": Expr(
                f'{document}.document_type == "Command" && can(regex("{DOCUMENT_NAME_PATTERN}", {document}.name)) && {document}.arn == format("arn:%s:ssm:%s:%s:document/%s", data.aws_partition.ssm_associations.partition, data.aws_region.ssm_associations.region, data.aws_caller_identity.ssm_associations.account_id, {document}.name) && can(regex("^[1-9][0-9]*$", {document}.latest_version))'
            ),
            "error_message": "Associations require a native versioned Command document in the deployment account, partition, and Region.",
        },
        {
            "condition": Expr(
                'can(regex("^i-([0-9a-f]{8}|[0-9a-f]{17})$", each.value.instance.id)) && each.value.instance.arn == format("arn:%s:ec2:%s:%s:instance/%s", data.aws_partition.ssm_associations.partition, data.aws_region.ssm_associations.region, data.aws_caller_identity.ssm_associations.account_id, each.value.instance.id) && startswith(each.value.instance.profile_arn, format("arn:%s:iam::%s:instance-profile/", data.aws_partition.ssm_associations.partition, data.aws_caller_identity.ssm_associations.account_id))'
            ),
            "error_message": "Association targets require an explicit native EC2 instance and managed profile in the deployment scope.",
        },
        {
            "condition": Expr(
                "each.value.utc_hour >= 0 && each.value.utc_hour <= 23 && floor(each.value.utc_hour) == each.value.utc_hour && each.value.utc_minute >= 0 && each.value.utc_minute <= 59 && floor(each.value.utc_minute) == each.value.utc_minute"
            ),
            "error_message": "Daily schedules require integral UTC hours 0–23 and minutes 0–59.",
        },
        {
            "condition": Expr(
                f'try(tostring(local.ssm_association_document.schemaVersion) == "2.2" && length(local.ssm_association_document.mainSteps) > 0, false) && contains(["JSON", "YAML"], {document}.document_format) && ({document}.document_format == "YAML" || can(jsondecode({document}.content)))'
            ),
            "error_message": "Associations require executable schema 2.2 JSON or YAML document content.",
        },
        {
            "condition": Expr(
                'try(alltrue([for key, value in each.value.parameters : local.ssm_association_parameters[key].type == "String"]) && alltrue([for key, declaration in local.ssm_association_parameters : can(declaration.default) || contains(keys(each.value.parameters), key)]), false)'
            ),
            "error_message": "Overrides must supply declared String parameters and satisfy required parameters; StringList overrides are unsupported.",
        },
    ]


def render_associations(name: str, renderer: HCLRenderer) -> str:
    document = f"aws_ssm_document.{name}"
    content = 'data "aws_partition" "ssm_associations" {}\ndata "aws_region" "ssm_associations" {}\ndata "aws_caller_identity" "ssm_associations" {}\n\n'
    content += f"locals {{\n  ssm_association_document = try(yamldecode({document}.content), {{}})\n  ssm_association_parameters = try(local.ssm_association_document.parameters, {{}})\n}}\n\n"
    return content + renderer.render_resource(
        "aws_ssm_association",
        "ec2",
        {
            "for_each": Expr("var.ec2_associations"),
            "name": Expr(f"{document}.name"),
            "document_version": Expr(f"{document}.latest_version"),
            "association_name": Expr('format("iacc-%s", each.key)'),
            "targets": {
                "key": "InstanceIds",
                "values": [Expr("each.value.instance.id")],
            },
            "parameters": Expr("each.value.parameters"),
            "schedule_expression": Expr(
                'format("cron(%d %d ? * * *)", each.value.utc_minute, each.value.utc_hour)'
            ),
            "apply_only_at_cron_interval": Expr("!each.value.apply_immediately"),
            "max_concurrency": "1",
            "max_errors": "0",
            "lifecycle": {"precondition": association_preconditions(document)},
        },
    )


def render_ssm_node(name: str, renderer: HCLRenderer) -> str:
    return 'data "aws_partition" "ssm_node" {}\n\n' + renderer.render_resource(
        "aws_iam_role_policy_attachment",
        "ssm_core",
        {
            "role": Expr(f"aws_iam_role.{name}_role.name"),
            "policy_arn": Expr(
                'format("arn:%s:iam::aws:policy/AmazonSSMManagedInstanceCore", data.aws_partition.ssm_node.partition)'
            ),
        },
    )
