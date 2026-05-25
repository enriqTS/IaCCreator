"""Unit tests for analytics-to-games service type registration.

Validates:
- All 25 full-generator ServiceType enum members exist with correct values
- All 63 icon-only ServiceType enum members exist with correct values
- All 25 full-generator services are in GENERATOR_REGISTRY
- No icon-only services are in GENERATOR_REGISTRY
- ResourceConfig has all new optional fields for 25 full-generator services
- All 25 full-generator services have entries in VARIABLE_SCHEMAS
- FileTreeAssembler skips icon-only service modules
- FileTreeAssembler produces files for full-generator services alongside icon-only services

Requirements: 1.1, 3.1, 5.1, 7.1, 9.1, 11.1, 13.1, 15.1, 17.1, 19.1, 21.1, 23.1, 25.1,
27.1, 29.1, 31.1, 33.1, 35.1, 37.1, 39.1, 41.1, 43.1, 45.1, 47.1, 49.1, 52.1–52.76, 53.1–53.3
"""

import pytest

from app.models.input_models import ResourceConfig, ServiceType
from app.generators.registry import GENERATOR_REGISTRY
from app.generators.variable_schemas import VARIABLE_SCHEMAS
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
    # Analytics
    "ATHENA": "athena",
    "CLOUDSEARCH": "cloudsearch",
    "EMR": "emr",
    "GLUE": "glue",
    "KINESIS": "kinesis",
    "KINESIS_FIREHOSE": "kinesis-firehose",
    "MSK": "msk",
    "OPENSEARCH": "opensearch",
    "REDSHIFT": "redshift",
    # Business Applications
    "CONNECT": "connect",
    "SES": "ses",
    "PINPOINT": "pinpoint",
    # Database
    "AURORA": "aurora",
    "DOCUMENTDB": "documentdb",
    "ELASTICACHE": "elasticache",
    "NEPTUNE": "neptune",
    "RDS": "rds",
    "TIMESTREAM": "timestream",
    # Developer Tools
    "CODEBUILD": "codebuild",
    "CODECOMMIT": "codecommit",
    "CODEDEPLOY": "codedeploy",
    "CODEPIPELINE": "codepipeline",
    # End User Computing
    "APPSTREAM": "appstream",
    # Front End Web Mobile
    "AMPLIFY": "amplify",
    # Games
    "GAMELIFT": "gamelift",
}

ICON_ONLY_SERVICES = {
    # Analytics icon-only
    "CLEAN_ROOMS": "clean-rooms",
    "DATA_EXCHANGE": "data-exchange",
    "DATA_PIPELINE": "data-pipeline",
    "DATAZONE": "datazone",
    "FINSPACE": "finspace",
    "GLUE_DATABREW": "glue-databrew",
    "GLUE_ELASTIC_VIEWS": "glue-elastic-views",
    "KINESIS_DATA_ANALYTICS": "kinesis-data-analytics",
    "KINESIS_DATA_STREAMS": "kinesis-data-streams",
    "KINESIS_VIDEO_STREAMS": "kinesis-video-streams",
    "LAKE_FORMATION": "lake-formation",
    "QUICKSIGHT": "quicksight",
    # Blockchain icon-only
    "MANAGED_BLOCKCHAIN": "managed-blockchain",
    "QUANTUM_LEDGER_DATABASE": "quantum-ledger-database",
    # Business Applications icon-only
    "ALEXA_FOR_BUSINESS": "alexa-for-business",
    "CHIME_SDK": "chime-sdk",
    "CHIME_VOICE_CONNECTOR": "chime-voice-connector",
    "CHIME": "chime",
    "HONEYCODE": "honeycode",
    "PINPOINT_APIS": "pinpoint-apis",
    "SUPPLY_CHAIN": "supply-chain",
    "WICKR": "wickr",
    "WORKDOCS_SDK": "workdocs-sdk",
    "WORKDOCS": "workdocs",
    "WORKMAIL": "workmail",
    # Cloud Financial Management icon-only
    "APPLICATION_COST_PROFILER": "application-cost-profiler",
    "BILLING_CONDUCTOR": "billing-conductor",
    "BUDGETS": "budgets",
    "COST_AND_USAGE_REPORT": "cost-and-usage-report",
    "COST_EXPLORER": "cost-explorer",
    "RESERVED_INSTANCE_REPORTING": "reserved-instance-reporting",
    "SAVINGS_PLANS": "savings-plans",
    # Customer Enablement icon-only
    "ACTIVATE": "activate",
    "IQ": "iq",
    "MANAGED_SERVICES": "managed-services",
    "PROFESSIONAL_SERVICES": "professional-services",
    "REPOST": "repost",
    "SUPPORT": "support",
    "TRAINING_CERTIFICATION": "training-certification",
    # Database icon-only
    "DATABASE_MIGRATION_SERVICE": "database-migration-service",
    "KEYSPACES": "keyspaces",
    "MEMORYDB": "memorydb",
    "RDS_ON_VMWARE": "rds-on-vmware",
    # Developer Tools icon-only
    "APPLICATION_COMPOSER": "application-composer",
    "CLOUD_CONTROL_API": "cloud-control-api",
    "CLOUD_DEVELOPMENT_KIT": "cloud-development-kit",
    "CLOUD9": "cloud9",
    "CLOUDSHELL": "cloudshell",
    "CODEARTIFACT": "codeartifact",
    "CODECATALYST": "codecatalyst",
    "CODESTAR": "codestar",
    "COMMAND_LINE_INTERFACE": "command-line-interface",
    "CORRETTO": "corretto",
    "TOOLS_AND_SDKS": "tools-and-sdks",
    "X_RAY": "x-ray",
    # End User Computing icon-only
    "WORKLINK": "worklink",
    "WORKSPACES_FAMILY": "workspaces-family",
    # Front End Web Mobile icon-only
    "DEVICE_FARM": "device-farm",
    "LOCATION_SERVICE": "location-service",
    # Games icon-only
    "GAMEKIT": "gamekit",
    "GAMESPARKS": "gamesparks",
    "LUMBERYARD": "lumberyard",
    "OPEN_3D_ENGINE": "open-3d-engine",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_instance(name: str, service_type: ServiceType) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for the given service type."""
    return ResourceInstanceIR(
        name=name,
        service_type=service_type,
        config=ResourceConfig(),
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
    """Verify all 25 full-generator ServiceType enum members exist with correct values."""

    @pytest.mark.parametrize("member_name,expected_value", FULL_GENERATOR_SERVICES.items())
    def test_enum_member_exists(self, member_name: str, expected_value: str):
        member = ServiceType[member_name]
        assert member.value == expected_value


# ---------------------------------------------------------------------------
# 2. Icon-only ServiceType enum members
# ---------------------------------------------------------------------------

class TestIconOnlyServiceTypeEnum:
    """Verify all 63 icon-only ServiceType enum members exist with correct values."""

    @pytest.mark.parametrize("member_name,expected_value", ICON_ONLY_SERVICES.items())
    def test_enum_member_exists(self, member_name: str, expected_value: str):
        member = ServiceType[member_name]
        assert member.value == expected_value


# ---------------------------------------------------------------------------
# 3. Full-generator services in GENERATOR_REGISTRY
# ---------------------------------------------------------------------------

class TestGeneratorRegistry:
    """Verify all 25 full-generator services are in GENERATOR_REGISTRY."""

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
# 4. ResourceConfig optional fields for full-generator services
# ---------------------------------------------------------------------------

class TestResourceConfigFields:
    """Verify ResourceConfig has all new optional fields for 25 full-generator services."""

    # Analytics fields
    @pytest.mark.parametrize("field", [
        "athena_name", "cloudsearch_name",
        "emr_release_label", "emr_service_role",
        "glue_catalog_database_name",
        "kinesis_shard_count",
        "firehose_destination",
        "msk_kafka_version", "msk_number_of_broker_nodes",
        "opensearch_domain_name",
        "redshift_node_type", "redshift_master_username",
    ])
    def test_analytics_fields(self, field: str):
        config = ResourceConfig()
        assert hasattr(config, field)
        assert getattr(config, field) is None

    # Business Applications fields
    @pytest.mark.parametrize("field", [
        "connect_identity_management_type",
        "connect_inbound_calls_enabled",
        "connect_outbound_calls_enabled",
        "ses_domain",
        "pinpoint_name",
    ])
    def test_business_applications_fields(self, field: str):
        config = ResourceConfig()
        assert hasattr(config, field)
        assert getattr(config, field) is None

    # Database fields
    @pytest.mark.parametrize("field", [
        "aurora_engine", "aurora_master_username",
        "documentdb_master_username",
        "elasticache_engine", "elasticache_node_type", "elasticache_num_cache_nodes",
        "neptune_cluster_identifier",
        "rds_engine", "rds_instance_class", "rds_allocated_storage", "rds_username",
        "timestream_database_name",
    ])
    def test_database_fields(self, field: str):
        config = ResourceConfig()
        assert hasattr(config, field)
        assert getattr(config, field) is None

    # Developer Tools fields
    @pytest.mark.parametrize("field", [
        "codebuild_source_type", "codebuild_service_role",
        "codecommit_repository_name",
        "codedeploy_compute_platform",
        "codepipeline_role_arn",
    ])
    def test_developer_tools_fields(self, field: str):
        config = ResourceConfig()
        assert hasattr(config, field)
        assert getattr(config, field) is None

    # End User Computing fields
    @pytest.mark.parametrize("field", ["appstream_instance_type"])
    def test_end_user_computing_fields(self, field: str):
        config = ResourceConfig()
        assert hasattr(config, field)
        assert getattr(config, field) is None

    # Front End Web Mobile fields
    @pytest.mark.parametrize("field", ["amplify_name"])
    def test_front_end_web_mobile_fields(self, field: str):
        config = ResourceConfig()
        assert hasattr(config, field)
        assert getattr(config, field) is None

    # Games fields
    @pytest.mark.parametrize("field", ["gamelift_ec2_instance_type"])
    def test_games_fields(self, field: str):
        config = ResourceConfig()
        assert hasattr(config, field)
        assert getattr(config, field) is None


# ---------------------------------------------------------------------------
# 5. Variable schemas for full-generator services
# ---------------------------------------------------------------------------

class TestVariableSchemas:
    """Verify all 25 full-generator services have entries in VARIABLE_SCHEMAS."""

    @pytest.mark.parametrize("member_name", FULL_GENERATOR_SERVICES.keys())
    def test_service_has_variable_schema(self, member_name: str):
        service_type = ServiceType[member_name]
        assert service_type in VARIABLE_SCHEMAS, (
            f"{member_name} should have an entry in VARIABLE_SCHEMAS"
        )
        assert len(VARIABLE_SCHEMAS[service_type]) > 0, (
            f"{member_name} VARIABLE_SCHEMAS entry should not be empty"
        )


# ---------------------------------------------------------------------------
# 6. FileTreeAssembler skip behavior for icon-only services
# ---------------------------------------------------------------------------

class TestFileTreeAssemblerSkipBehavior:
    """Test that FileTreeAssembler skips icon-only service modules."""

    def test_icon_only_module_produces_no_files(self):
        """A ProjectIR with only an icon-only service module produces no module files."""
        icon_module = ServiceModuleIR(
            service_type=ServiceType.QUICKSIGHT,
            instances=[_make_instance("my-quicksight", ServiceType.QUICKSIGHT)],
        )
        project = _make_project([icon_module])

        assembler = FileTreeAssembler()
        tree = assembler.assemble(project)

        # No files should exist under modules/quicksight/
        module_files = [p for p in tree if "modules/quicksight" in p]
        assert module_files == [], (
            f"Expected no files for icon-only service, got: {module_files}"
        )

    def test_full_generator_produces_files_alongside_icon_only(self):
        """A ProjectIR with both full-generator and icon-only modules produces files
        only for the full-generator service."""
        athena_module = ServiceModuleIR(
            service_type=ServiceType.ATHENA,
            instances=[_make_instance("my-athena", ServiceType.ATHENA)],
        )
        quicksight_module = ServiceModuleIR(
            service_type=ServiceType.QUICKSIGHT,
            instances=[_make_instance("my-quicksight", ServiceType.QUICKSIGHT)],
        )
        project = _make_project([athena_module, quicksight_module])

        assembler = FileTreeAssembler()
        tree = assembler.assemble(project)

        # Athena module files should exist
        athena_files = [p for p in tree if "modules/analytics/athena" in p]
        assert len(athena_files) > 0, "Expected files for Athena full-generator service"

        # QuickSight module files should NOT exist
        quicksight_files = [p for p in tree if "modules/quicksight" in p or "modules/other/quicksight" in p]
        assert quicksight_files == [], (
            f"Expected no files for icon-only QuickSight service, got: {quicksight_files}"
        )
