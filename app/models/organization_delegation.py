from dataclasses import dataclass

from app.models.input_models._general import ServiceType


@dataclass(frozen=True)
class DelegatedService:
    service: ServiceType
    principal: str
    resource: str
    account_argument: str
    regional: bool = True


DELEGATED_SERVICES = (
    DelegatedService(
        ServiceType.GUARDDUTY,
        "guardduty.amazonaws.com",
        "aws_guardduty_organization_admin_account",
        "admin_account_id",
    ),
    DelegatedService(
        ServiceType.SECURITY_HUB,
        "securityhub.amazonaws.com",
        "aws_securityhub_organization_admin_account",
        "admin_account_id",
    ),
    DelegatedService(
        ServiceType.MACIE,
        "macie.amazonaws.com",
        "aws_macie2_organization_admin_account",
        "admin_account_id",
    ),
    DelegatedService(
        ServiceType.INSPECTOR,
        "inspector2.amazonaws.com",
        "aws_inspector2_delegated_admin_account",
        "account_id",
    ),
    DelegatedService(
        ServiceType.FIREWALL_MANAGER,
        "fms.amazonaws.com",
        "aws_fms_admin_account",
        "account_id",
        False,
    ),
)

DELEGATION_BY_SERVICE = {
    definition.service: definition for definition in DELEGATED_SERVICES
}

ORGANIZATION_CONTEXT_TYPE = "object({ id = string, arn = string, management_account_id = string, feature_set = string, service_principals = list(string), active_member_ids = list(string) })"
