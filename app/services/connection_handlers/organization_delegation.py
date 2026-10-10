from app.generators.hcl_renderer import Expr
from app.generators.organization_delegation import REGION, render_delegation
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.models.organization_delegation import ORGANIZATION_CONTEXT_TYPE
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.organization_delegation_bindings import (
    resolve_delegations,
)


class OrganizationDelegationHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        bindings = resolve_delegations(connection, project)
        binding = next(
            value for value in bindings if value.target.name == connection.target_name
        )
        binding.source.config._delegated_service_principals = sorted(
            {value.definition.principal for value in bindings}
        )
        peers = [
            peer
            for peer in project.connections
            if peer.source_name == connection.source_name
            and peer.target_name == connection.target_name
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        target = binding.target
        if target.service_type in {ServiceType.INSPECTOR, ServiceType.FIREWALL_MANAGER}:
            target.config._organization_delegation = True
        if (
            target.service_type == ServiceType.FIREWALL_MANAGER
            and not target.config.account_id
        ):
            target.config.account_id = binding.account_id
        resource_name = (
            "organization_admin" if binding.definition.regional else target.name
        )
        registration = f"{binding.definition.resource}.{resource_name}"
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=target.name,
                    name="organization_context",
                    type=ORGANIZATION_CONTEXT_TYPE,
                    value=f"module.{binding.source.name}.delegation_context",
                    description="Native organization, trusted access, and active membership",
                ),
                ModuleInput(
                    module=target.name,
                    name="delegated_admin_account_id",
                    type="string",
                    value=self._renderer.render_expression(binding.account_id),
                    description="Explicit existing delegated member",
                ),
            ],
            resources=[
                self._resource(
                    target.name,
                    "organization_delegation.tf",
                    render_delegation(target.name, binding.definition, self._renderer),
                )
            ],
            outputs=[
                self._output(
                    target.name,
                    "organization_delegation",
                    self._renderer.render_expression(
                        {
                            "account_id": Expr(
                                f"{registration}.{binding.definition.account_argument}"
                                if binding.definition.regional
                                else f"{registration}.id"
                            ),
                            "organization_id": Expr("var.organization_context.id"),
                            "management_account_id": Expr(
                                "var.organization_context.management_account_id"
                            ),
                            "service_principal": binding.definition.principal,
                            "region": Expr(REGION),
                        }
                    ),
                    "Native delegated administrator designation; other service resources remain in the management account",
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_delegations(connection, project)
        return [
            ConnectionIssue(
                severity="warning",
                message="Apply with organization management-account credentials. This designates an existing ACTIVE non-management member; the connected service resources still belong to the management account. Native service APIs can enable the delegated member service and incur charges. Import existing organizations, service enablements, and designations before applying; retain other trusted service principals in the organization configuration. Use one state owner for global organization/trusted access and each designation. The deployment identity needs service administration, Organizations trusted-access/registration, and service-linked-role permissions, supplied separately. Member-account providers, member enrollment, automatic fleet enablement, organization policies, central Security Hub configuration, and Firewall Manager policies/AWS Config prerequisites remain external. Removing an edge can revoke trusted access unless its principal is retained; removing a designation does not undo member service enablement or findings.",
            )
        ]
