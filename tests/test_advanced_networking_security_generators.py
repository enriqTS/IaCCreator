import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType, get_service_config_models
from app.models.input_models.client_vpn_config import ClientVpnConfig
from app.models.input_models.direct_connect_config import DirectConnectConfig
from app.models.input_models.firewall_manager_config import FirewallManagerConfig
from app.models.input_models.global_accelerator_config import GlobalAcceleratorConfig
from app.models.input_models.guardduty_config import GuardDutyConfig
from app.models.input_models.inspector_config import InspectorConfig
from app.models.input_models.macie_config import MacieConfig
from app.models.input_models.network_firewall_config import NetworkFirewallConfig
from app.models.input_models.private_certificate_authority_config import (
    PrivateCertificateAuthorityConfig,
)
from app.models.input_models.security_hub_config import SecurityHubConfig
from app.models.input_models.site_to_site_vpn_config import SiteToSiteVpnConfig
from app.models.input_models.transit_gateway_config import TransitGatewayConfig
from app.models.input_models.verified_permissions_config import (
    VerifiedPermissionsConfig,
)
from app.models.input_models.vpc_lattice_config import VpcLatticeConfig
from app.models.ir_models import ResourceInstanceIR

SERVICE_CONFIGS = {
    ServiceType.TRANSIT_GATEWAY: TransitGatewayConfig(),
    ServiceType.DIRECT_CONNECT: DirectConnectConfig(),
    ServiceType.NETWORK_FIREWALL: NetworkFirewallConfig(),
    ServiceType.GUARDDUTY: GuardDutyConfig(),
    ServiceType.SECURITY_HUB: SecurityHubConfig(),
    ServiceType.MACIE: MacieConfig(),
    ServiceType.INSPECTOR: InspectorConfig(),
    ServiceType.FIREWALL_MANAGER: FirewallManagerConfig(),
    ServiceType.PRIVATE_CERTIFICATE_AUTHORITY: PrivateCertificateAuthorityConfig(),
    ServiceType.VERIFIED_PERMISSIONS: VerifiedPermissionsConfig(),
    ServiceType.VPC_LATTICE: VpcLatticeConfig(),
    ServiceType.GLOBAL_ACCELERATOR: GlobalAcceleratorConfig(),
    ServiceType.SITE_TO_SITE_VPN: SiteToSiteVpnConfig(),
    ServiceType.CLIENT_VPN: ClientVpnConfig(),
}


@pytest.mark.parametrize(("service_type", "config"), SERVICE_CONFIGS.items())
def test_advanced_generators_emit_typed_terraform(service_type, config) -> None:
    instance = ResourceInstanceIR(
        name="advanced_resource", service_type=service_type, config=config
    )
    generator = GENERATOR_REGISTRY[service_type]
    assert 'resource "aws_' in generator.generate_resource_tf(instance)
    assert generator.generate_variables_tf(instance)
    assert generator.generate_outputs_tf(instance)
    assert get_service_config_models()[service_type].has_terraform_schema()


def test_network_firewall_uses_cross_module_inputs() -> None:
    instance = ResourceInstanceIR(
        name="firewall",
        service_type=ServiceType.NETWORK_FIREWALL,
        config=NetworkFirewallConfig(),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.NETWORK_FIREWALL].generate_resource_tf(
        instance
    )
    assert "vpc_id = var.vpc_id" in hcl
    assert "subnet_id = var.subnet_id" in hcl
    assert "firewall_policy_arn = var.firewall_policy_arn" in hcl


def test_client_vpn_uses_certificate_inputs() -> None:
    instance = ResourceInstanceIR(
        name="remote_access",
        service_type=ServiceType.CLIENT_VPN,
        config=ClientVpnConfig(),
    )
    hcl = GENERATOR_REGISTRY[ServiceType.CLIENT_VPN].generate_resource_tf(instance)
    assert "server_certificate_arn = var.server_certificate_arn" in hcl
    assert "root_certificate_chain_arn = var.root_certificate_chain_arn" in hcl
