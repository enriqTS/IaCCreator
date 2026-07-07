"""Unit tests for compute & container service type registration.

Validates:
- All 9 full-generator ServiceType enum members exist with correct values
- All 30 icon-only ServiceType enum members exist with correct values
- All 9 full-generator services are in GENERATOR_REGISTRY
- No icon-only services are in GENERATOR_REGISTRY
- ResourceConfig has all new optional fields for 9 full-generator services
- FileTreeAssembler skips icon-only service modules
- FileTreeAssembler produces files for full-generator services alongside icon-only services

Requirements: 1.1, 3.1, 5.1, 7.1, 9.1, 11.1, 13.1, 15.1, 17.1, 20.1–20.35, 21.1–21.3
"""

import pytest

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType
from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import get_service_config_models
from app.models.ir_models import (
    EnvironmentIR,
    GlobalTerraformConfigIR,
    ProjectIR,
    ResourceInstanceIR,
    ServiceModuleIR,
)
from app.services.file_tree_assembler import FileTreeAssembler

# ---------------------------------------------------------------------------
# Expected data
# ---------------------------------------------------------------------------

FULL_GENERATOR_SERVICES = {
    "EC2": "ec2",
    "ECS": "ecs",
    "EKS": "eks",
    "ELASTIC_BEANSTALK": "elastic-beanstalk",
    "APP_RUNNER": "app-runner",
    "BATCH": "batch",
    "EC2_IMAGE_BUILDER": "ec2-image-builder",
    "LIGHTSAIL": "lightsail",
    "ECR": "ecr",
}

ICON_ONLY_SERVICES = {
    # Compute icon-only
    "APPLICATION_AUTO_SCALING": "application-auto-scaling",
    "BOTTLEROCKET": "bottlerocket",
    "COMPUTE_OPTIMIZER": "compute-optimizer",
    "EC2_AUTO_SCALING": "ec2-auto-scaling",
    "ELASTIC_FABRIC_ADAPTER": "elastic-fabric-adapter",
    "FARGATE": "fargate",
    "GENOMICS_CLI": "genomics-cli",
    "LOCAL_ZONES": "local-zones",
    "NICE_DCV": "nice-dcv",
    "NICE_ENGINFRAME": "nice-enginframe",
    "NITRO_ENCLAVES": "nitro-enclaves",
    "OUTPOSTS_FAMILY": "outposts-family",
    "OUTPOSTS_RACK": "outposts-rack",
    "OUTPOSTS_SERVERS": "outposts-servers",
    "PARALLELCLUSTER": "parallelcluster",
    "SERVERLESS_APPLICATION_REPOSITORY": "serverless-application-repository",
    "SIMSPACE_WEAVER": "simspace-weaver",
    "THINKBOX_DEADLINE": "thinkbox-deadline",
    "THINKBOX_FROST": "thinkbox-frost",
    "THINKBOX_KRAKATOA": "thinkbox-krakatoa",
    "THINKBOX_SEQUOIA": "thinkbox-sequoia",
    "THINKBOX_STOKE": "thinkbox-stoke",
    "THINKBOX_XMESH": "thinkbox-xmesh",
    "VMWARE_CLOUD_ON_AWS": "vmware-cloud-on-aws",
    "WAVELENGTH": "wavelength",
    # Containers icon-only
    "ECS_ANYWHERE": "ecs-anywhere",
    "EKS_ANYWHERE": "eks-anywhere",
    "EKS_CLOUD": "eks-cloud",
    "EKS_DISTRO": "eks-distro",
    "RED_HAT_OPENSHIFT": "red-hat-openshift",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SERVICE_CONFIG_MODELS = get_service_config_models()


def _make_instance(name: str, service_type: ServiceType) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for the given service type."""
    config_cls = _SERVICE_CONFIG_MODELS.get(service_type, BaseServiceConfig)
    return ResourceInstanceIR(
        name=name,
        service_type=service_type,
        config=config_cls(),
    )


def _make_project(modules: list[ServiceModuleIR]) -> ProjectIR:
    """Create a minimal ProjectIR with the given modules."""
    return ProjectIR(
        project_name="test-project",
        environments=[
            EnvironmentIR(
                name="dev",
                variables={"region": "us-east-1"},
                module_refs=[m.service_type for m in modules],
            )
        ],
        modules=modules,
        connections=[],
        global_config=GlobalTerraformConfigIR(),
    )


# ---------------------------------------------------------------------------
# 1. Full-generator ServiceType enum members
# ---------------------------------------------------------------------------


class TestFullGeneratorServiceTypeEnum:
    """Verify all 9 full-generator ServiceType enum members exist with correct values."""

    @pytest.mark.parametrize(
        "member_name,expected_value", FULL_GENERATOR_SERVICES.items()
    )
    def test_enum_member_exists(self, member_name: str, expected_value: str):
        member = ServiceType[member_name]
        assert member.value == expected_value


# ---------------------------------------------------------------------------
# 2. Icon-only ServiceType enum members
# ---------------------------------------------------------------------------


class TestIconOnlyServiceTypeEnum:
    """Verify all 30 icon-only ServiceType enum members exist with correct values."""

    @pytest.mark.parametrize("member_name,expected_value", ICON_ONLY_SERVICES.items())
    def test_enum_member_exists(self, member_name: str, expected_value: str):
        member = ServiceType[member_name]
        assert member.value == expected_value


# ---------------------------------------------------------------------------
# 3. Full-generator services in GENERATOR_REGISTRY
# ---------------------------------------------------------------------------


class TestGeneratorRegistry:
    """Verify all 9 full-generator services are in GENERATOR_REGISTRY."""

    @pytest.mark.parametrize("member_name", FULL_GENERATOR_SERVICES.keys())
    def test_full_generator_in_registry(self, member_name: str):
        service_type = ServiceType[member_name]
        assert service_type in GENERATOR_REGISTRY, (
            f"{member_name} should be in GENERATOR_REGISTRY"
        )

    @pytest.mark.parametrize("member_name", ICON_ONLY_SERVICES.keys())
    def test_icon_only_not_in_registry(self, member_name: str):
        service_type = ServiceType[member_name]
        assert service_type not in GENERATOR_REGISTRY, (
            f"Icon-only service {member_name} should NOT be in GENERATOR_REGISTRY"
        )


# ---------------------------------------------------------------------------
# 4. Typed config models for full-generator services (replaces ResourceConfig)
# ---------------------------------------------------------------------------

# TestResourceConfigFields removed — ResourceConfig god-object has been deleted.
# Per-service typed configs (Ec2Config, EcsConfig, etc.) are tested via
# their own modules and property-based tests.


# ---------------------------------------------------------------------------
# 5. FileTreeAssembler skip behavior for icon-only services
# ---------------------------------------------------------------------------


class TestFileTreeAssemblerSkipBehavior:
    """Test that FileTreeAssembler skips icon-only service modules."""

    def test_icon_only_module_produces_no_files(self):
        """A ProjectIR with only an icon-only service module produces no module files."""
        icon_module = ServiceModuleIR(
            service_type=ServiceType.FARGATE,
            instances=[_make_instance("my-fargate", ServiceType.FARGATE)],
        )
        project = _make_project([icon_module])

        assembler = FileTreeAssembler()
        tree = assembler.assemble(project)

        # No files should exist under modules/fargate/
        module_files = [p for p in tree if "modules/fargate" in p]
        assert module_files == [], (
            f"Expected no files for icon-only service, got: {module_files}"
        )

    def test_full_generator_produces_files_alongside_icon_only(self):
        """A ProjectIR with both full-generator and icon-only modules produces files
        only for the full-generator service."""
        ec2_module = ServiceModuleIR(
            service_type=ServiceType.EC2,
            instances=[_make_instance("my-server", ServiceType.EC2)],
        )
        fargate_module = ServiceModuleIR(
            service_type=ServiceType.FARGATE,
            instances=[_make_instance("my-fargate", ServiceType.FARGATE)],
        )
        project = _make_project([ec2_module, fargate_module])

        assembler = FileTreeAssembler()
        tree = assembler.assemble(project)

        # EC2 module files should exist
        ec2_files = [p for p in tree if "modules/compute/ec2" in p]
        assert len(ec2_files) > 0, "Expected files for EC2 full-generator service"

        # Fargate module files should NOT exist
        fargate_files = [
            p for p in tree if "modules/fargate" in p or "modules/other/fargate" in p
        ]
        assert fargate_files == [], (
            f"Expected no files for icon-only Fargate service, got: {fargate_files}"
        )
