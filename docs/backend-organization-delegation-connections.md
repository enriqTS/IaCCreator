# Organizations security delegated administration

Organizations connects to GuardDuty, Security Hub CSPM, Macie, Inspector, and Firewall Manager through `delegates_admin`. Every connection requires `account_id`, a literal nonzero twelve-digit ID of an existing ACTIVE non-management member.

## Account scope

Apply with the organization's management-account credentials. The generator has regional providers, but no member-account assume-role providers. GuardDuty detectors, Security Hub enablement, Macie enablement, and Inspector scanning therefore remain in the management account. The edge designates the selected member through the service's native organization API; it does not move these resources into that member. Firewall Manager's existing administrator resource already represents the selected member.

Native designation APIs can enable services in the delegated member and incur charges. Configure member-account resources, account enrollment, scanning settings, auto-enable behavior, Security Hub central configuration, and organization policies separately. Firewall Manager also needs its AWS Config and other service prerequisites supplied separately. The connection does not create Firewall Manager policies.

## Resource ownership

| Target | Designation resource | Account argument | Scope |
|---|---|---|---|
| GuardDuty | `aws_guardduty_organization_admin_account` | `admin_account_id` | Target Region |
| Security Hub CSPM | `aws_securityhub_organization_admin_account` | `admin_account_id` | Target Region |
| Macie | `aws_macie2_organization_admin_account` | `admin_account_id` | Target Region |
| Inspector | `aws_inspector2_delegated_admin_account` | `account_id` | Target Region |
| Firewall Manager | Existing `aws_fms_admin_account` | `account_id` | Commercial partition, `us-east-1` |

The target module owns the designation. No additional generic `aws_organizations_delegated_administrator` resource is created: the native service API owns registration. Firewall Manager reuses its existing resource, fills an empty administrator setting from the connection, and rejects a conflicting setting. Terraform overrides must still match the connection's member ID.

Connected Inspector enables only the calling management account. An empty `account_ids` list resolves to the caller's native ID; a configured list must contain exactly that account. At least one scan type is required. This does not enable scanning for the organization's member fleet.

One organization owns all connected delegations. Each service uses the same administrator across Regions and has one node per effective Region. Other nodes of that same account-level service in that Region are rejected, including unconnected nodes. Environment Region overrides cannot collapse distinct nodes into one Region. Firewall Manager has one global owner. Different services may select different members. Identical duplicate edges are idempotent; conflicting duplicates fail.

## Trusted access and native checks

The organization must already use `ALL` features. The connection rejects a billing-only configuration and does not change the configured feature set; complete any existing organization's feature upgrade separately before importing it into this project. The organization resource owns trusted access and unions connected service principals with editable `aws_service_access_principals`. List all unrelated existing trusted principals in that field before applying so Terraform preserves them.

The source exports a typed `delegation_context` containing its native ID, ARN, management account ID, feature set, trusted principals, and ACTIVE non-management member IDs. Membership uses the provider's `state` field rather than deprecated account `status`. Target inputs consume this output without a reverse module dependency.

Terraform preconditions verify organization identity against the native partition and caller, all features, trusted access, and selected active membership. Regional services also verify their native management-account enablement and scope. Firewall Manager checks the commercial partition, `us-east-1`, and its existing administrator input. An environment override to billing-only features fails the organization resource precondition.

The deployment identity needs service administrative APIs, Organizations trusted-access and delegated-registration permissions, and service-linked-role creation permissions as applicable. These deployment permissions are external; the connection does not grant IAM to the operator.

## Existing state and removal

Import an existing organization, account-level service enablements, and existing designations into the generated addresses before applying. A newly created organization has no eligible member and fails the membership precondition until the account is joined separately. Account creation, invitations, feature upgrades, and migration from an existing administrator are external operations.

Global organization/trusted-access resources and each regional designation need one Terraform state owner. Generated environment directories are alternative deployment configurations; applying several directories to the same organization duplicates ownership. A multi-Region diagram can manage all target Regions from one selected environment while retaining one organization owner.

Deleting the last edge for a service removes its automatically contributed trusted principal unless it remains in `aws_service_access_principals`. Removing a designation can change administrator/member relationships and does not undo service enablement, scanning charges, or previously collected findings. Review existing organizational configuration before changing administrator ownership.

## Verification and references

Tests cover all five native resources, strict IDs, account and Region conflicts, duplicate/order properties, trusted-principal preservation, management/member scope guards, schema discovery, and real AWS-provider validation plus dependency graphs. No AWS API calls or live account provisioning are performed.

Provider references: [Organizations](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/organizations_organization), [GuardDuty](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_organization_admin_account), [Security Hub](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_organization_admin_account), [Macie](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/macie2_organization_admin_account), [Inspector](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/inspector2_delegated_admin_account), and [Firewall Manager](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fms_admin_account).

AWS administration guidance: [GuardDuty](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_organizations.html), [Security Hub CSPM](https://docs.aws.amazon.com/securityhub/latest/userguide/designate-orgs-admin-account.html), [Macie](https://docs.aws.amazon.com/macie/latest/user/accounts-mgmt-ao-notes.html), [Inspector](https://docs.aws.amazon.com/organizations/latest/userguide/services-that-can-integrate-inspector2.html), and [Firewall Manager prerequisites](https://docs.aws.amazon.com/waf/latest/developerguide/fms-prereq.html).
