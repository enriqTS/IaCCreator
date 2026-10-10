from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.organization_delegation import DelegatedService

CALLER = "data.aws_caller_identity.organization_delegation.account_id"
PARTITION = "data.aws_partition.organization_delegation.partition"
REGION = "data.aws_region.organization_delegation.region"


def precondition(condition: str, message: str) -> dict:
    return {"condition": Expr(condition), "error_message": message}


def delegation_preconditions(definition: DelegatedService) -> list[dict]:
    return [
        precondition(
            f'var.organization_context.management_account_id == {CALLER} && var.organization_context.feature_set == "ALL" && can(regex("^o-[a-z0-9]{{10,32}}$", var.organization_context.id)) && var.organization_context.arn == format("arn:%s:organizations::%s:organization/%s", {PARTITION}, {CALLER}, var.organization_context.id)',
            "Delegation requires the native all-features organization and its management-account credentials.",
        ),
        precondition(
            f'contains(var.organization_context.service_principals, "{definition.principal}")',
            "Enable the connected service's trusted access in the owning organization.",
        ),
        precondition(
            f'can(regex("^[0-9]{{12}}$", var.delegated_admin_account_id)) && var.delegated_admin_account_id != "000000000000" && var.delegated_admin_account_id != {CALLER} && contains(var.organization_context.active_member_ids, var.delegated_admin_account_id)',
            "Choose an existing ACTIVE non-management member of this organization.",
        ),
    ]


def guardduty_ready(name: str) -> str:
    ref = f"aws_guardduty_detector.{name}"
    return f'{ref}.enable && {ref}.account_id == {CALLER} && {ref}.arn == format("arn:%s:guardduty:%s:%s:detector/%s", {PARTITION}, {REGION}, {CALLER}, {ref}.id)'


def securityhub_ready(name: str) -> str:
    return f'aws_securityhub_account.{name}.arn == format("arn:%s:securityhub:%s:%s:hub/default", {PARTITION}, {REGION}, {CALLER})'


def macie_ready(name: str) -> str:
    ref = f"aws_macie2_account.{name}"
    return f'{ref}.status == "ENABLED" && startswith({ref}.service_role, format("arn:%s:iam::%s:role/aws-service-role/macie.amazonaws.com/", {PARTITION}, {CALLER}))'


def inspector_ready(name: str) -> str:
    ref = f"aws_inspector2_enabler.{name}"
    return f"toset({ref}.account_ids) == toset([{CALLER}]) && length({ref}.resource_types) > 0"


READINESS = {
    "guardduty": guardduty_ready,
    "security-hub": securityhub_ready,
    "macie": macie_ready,
    "inspector": inspector_ready,
}


def firewall_preconditions(definition: DelegatedService) -> list[dict]:
    return [
        *delegation_preconditions(definition),
        precondition(
            f'{PARTITION} == "aws" && {REGION} == "us-east-1" && var.account_id == var.delegated_admin_account_id',
            "Firewall Manager delegation supports the commercial partition in us-east-1 and must match its administrator input.",
        ),
    ]


def render_delegation(
    name: str, definition: DelegatedService, renderer: HCLRenderer
) -> str:
    identity = (
        "\n".join(
            f'data "{kind}" "organization_delegation" {{}}'
            for kind in ("aws_caller_identity", "aws_partition", "aws_region")
        )
        + "\n"
    )
    if not definition.regional:
        return identity
    return identity + renderer.render_resource(
        definition.resource,
        "organization_admin",
        {
            definition.account_argument: Expr("var.delegated_admin_account_id"),
            "lifecycle": {
                "precondition": [
                    *delegation_preconditions(definition),
                    precondition(
                        READINESS[definition.service.value](name),
                        "The connected service must be enabled in the management account and target Region.",
                    ),
                ]
            },
        },
    )
