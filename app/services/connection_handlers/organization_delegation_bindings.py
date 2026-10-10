import re
from dataclasses import dataclass

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.organization_delegation import (
    OrganizationDelegationConfig,
)
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR, ResourceInstanceIR
from app.models.organization_delegation import DELEGATION_BY_SERVICE, DelegatedService
from app.services.connection_handlers.base import BaseConnectionHandler


@dataclass(frozen=True)
class DelegationBinding:
    source: ResourceInstanceIR
    target: ResourceInstanceIR
    account_id: str
    definition: DelegatedService


def guardduty_config(target: ResourceInstanceIR, account_id: str) -> None:
    if not target.config.enabled:
        raise ValueError(
            "Delegation requires an enabled management-account GuardDuty detector"
        )


def macie_config(target: ResourceInstanceIR, account_id: str) -> None:
    if target.config.status != "ENABLED":
        raise ValueError("Delegation requires enabled management-account Macie")


def inspector_config(target: ResourceInstanceIR, account_id: str) -> None:
    accounts = target.config.account_ids
    if (
        not target.config.resource_types
        or len(accounts) > 1
        or any(
            not re.fullmatch(r"[0-9]{12}", value)
            or value in {account_id, "000000000000"}
            for value in accounts
        )
    ):
        raise ValueError(
            "Connected Inspector scans only the management account; leave account_ids empty or select that single account, and enable at least one scan type"
        )


def firewall_config(target: ResourceInstanceIR, account_id: str) -> None:
    if target.config.account_id and target.config.account_id != account_id:
        raise ValueError(
            "Firewall Manager's account_id must match the delegated member"
        )


CONFIG_CHECKS = {
    ServiceType.GUARDDUTY: guardduty_config,
    ServiceType.MACIE: macie_config,
    ServiceType.INSPECTOR: inspector_config,
    ServiceType.FIREWALL_MANAGER: firewall_config,
}


def resolve_delegations(
    connection: ConnectionIR, project: ProjectIR
) -> list[DelegationBinding]:
    peers = [
        peer
        for peer in project.connections
        if peer.source_service == ServiceType.ORGANIZATIONS
        and peer.target_service in DELEGATION_BY_SERVICE
    ]
    try:
        instances = [
            instance for module in project.modules for instance in module.instances
        ]
        if (
            len({peer.source_name for peer in peers}) != 1
            or sum(
                instance.service_type == ServiceType.ORGANIZATIONS
                for instance in instances
            )
            != 1
        ):
            raise ValueError(
                "One management-account organization must own all security delegations"
            )
        bindings = {}
        accounts = {}
        for peer in peers:
            source = BaseConnectionHandler._find_instance(peer.source_name, project)
            target = BaseConnectionHandler._find_instance(peer.target_name, project)
            settings = OrganizationDelegationConfig.model_validate(
                peer.connection_config
            )
            definition = DELEGATION_BY_SERVICE[peer.target_service]
            if source.config.feature_set != "ALL":
                raise ValueError(
                    "Security delegation requires ALL features; upgrading a billing-only organization is outside this connection"
                )
            previous = bindings.get(target.name)
            if previous and previous.account_id != settings.account_id:
                raise ValueError(
                    "Repeated delegations for one target must select the same member"
                )
            if (
                definition.service in accounts
                and accounts[definition.service] != settings.account_id
            ):
                raise ValueError(
                    "A service must use the same delegated administrator across all Regions"
                )
            accounts[definition.service] = settings.account_id
            check = CONFIG_CHECKS.get(definition.service)
            if check:
                check(target, settings.account_id)
            for environment in project.environments:
                region = (
                    environment.variables.get("region")
                    or target.provider_region
                    or project.global_config.provider_region
                )
                if not definition.regional and region != "us-east-1":
                    raise ValueError(
                        "Firewall Manager delegation requires us-east-1 in every environment"
                    )
                for instance in instances:
                    other_region = (
                        environment.variables.get("region")
                        or instance.provider_region
                        or project.global_config.provider_region
                    )
                    if (
                        instance.service_type == definition.service
                        and instance.name != target.name
                        and (not definition.regional or region == other_region)
                    ):
                        raise ValueError(
                            "Connected account-level services cannot share a Region with another node of the same service"
                        )
            bindings[target.name] = DelegationBinding(
                source, target, settings.account_id, definition
            )
        return [bindings[name] for name in sorted(bindings)]
    except ValueError as exc:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": ("delegation",), "msg": str(exc)}],
        ) from exc
