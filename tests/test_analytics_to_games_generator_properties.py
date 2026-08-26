"""Property-based tests for analytics-to-games service generators.

Feature: analytics-to-games-services
Uses Hypothesis to verify universal correctness properties across all
new analytics-to-games generators and the pipeline skip behavior.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.generators.registry import GENERATOR_REGISTRY
from app.generators.service_category_map import get_category
from app.models.input_models import ServiceType
from app.models.input_models._base import BaseServiceConfig
from app.models.input_models.amplify_config import AmplifyConfig
from app.models.input_models.appstream_config import AppStreamConfig
from app.models.input_models.athena_config import AthenaConfig
from app.models.input_models.aurora_config import AuroraConfig
from app.models.input_models.cloudsearch_config import CloudSearchConfig
from app.models.input_models.codebuild_config import CodeBuildConfig
from app.models.input_models.codecommit_config import CodeCommitConfig
from app.models.input_models.codedeploy_config import CodeDeployConfig
from app.models.input_models.codepipeline_config import CodePipelineConfig
from app.models.input_models.connect_config import ConnectConfig
from app.models.input_models.documentdb_config import DocumentDbConfig
from app.models.input_models.elasticache_config import ElastiCacheConfig
from app.models.input_models.emr_config import EmrConfig
from app.models.input_models.gamelift_config import GameLiftConfig
from app.models.input_models.glue_config import GlueConfig
from app.models.input_models.kinesis_config import KinesisConfig
from app.models.input_models.kinesis_firehose_config import KinesisFirehoseConfig
from app.models.input_models.msk_config import MskConfig
from app.models.input_models.neptune_config import NeptuneConfig
from app.models.input_models.opensearch_config import OpenSearchConfig
from app.models.input_models.pinpoint_config import PinpointConfig
from app.models.input_models.rds_config import RdsConfig
from app.models.input_models.redshift_config import RedshiftConfig
from app.models.input_models.ses_config import SesConfig
from app.models.input_models.timestream_config import TimestreamConfig
from app.models.ir_models import (
    EnvironmentIR,
    ProjectIR,
    ResourceInstanceIR,
    ServiceModuleIR,
)
from app.services.file_tree_assembler import FileTreeAssembler

# Mapping from service type to typed config class for migrated services
_TYPED_CONFIG_CLASSES: dict[ServiceType, type[BaseServiceConfig]] = {
    # Analytics
    ServiceType.ATHENA: AthenaConfig,
    ServiceType.CLOUDSEARCH: CloudSearchConfig,
    ServiceType.EMR: EmrConfig,
    ServiceType.GLUE: GlueConfig,
    ServiceType.KINESIS: KinesisConfig,
    ServiceType.KINESIS_FIREHOSE: KinesisFirehoseConfig,
    ServiceType.MSK: MskConfig,
    ServiceType.OPENSEARCH: OpenSearchConfig,
    ServiceType.REDSHIFT: RedshiftConfig,
    # Database
    ServiceType.AURORA: AuroraConfig,
    ServiceType.DOCUMENTDB: DocumentDbConfig,
    ServiceType.ELASTICACHE: ElastiCacheConfig,
    ServiceType.NEPTUNE: NeptuneConfig,
    ServiceType.RDS: RdsConfig,
    ServiceType.TIMESTREAM: TimestreamConfig,
    # Business Applications
    ServiceType.CONNECT: ConnectConfig,
    ServiceType.SES: SesConfig,
    ServiceType.PINPOINT: PinpointConfig,
    # Developer Tools
    ServiceType.CODEBUILD: CodeBuildConfig,
    ServiceType.CODECOMMIT: CodeCommitConfig,
    ServiceType.CODEDEPLOY: CodeDeployConfig,
    ServiceType.CODEPIPELINE: CodePipelineConfig,
    # End User Computing
    ServiceType.APPSTREAM: AppStreamConfig,
    # Front End Web Mobile
    ServiceType.AMPLIFY: AmplifyConfig,
    # Games
    ServiceType.GAMELIFT: GameLiftConfig,
}

# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

_resource_name_st = st.from_regex(r"[a-z][a-z0-9\-]{0,14}", fullmatch=True)

# The 25 full-generator analytics-to-games service types
FULL_GENERATOR_SERVICES = [
    ServiceType.ATHENA,
    ServiceType.CLOUDSEARCH,
    ServiceType.EMR,
    ServiceType.GLUE,
    ServiceType.KINESIS,
    ServiceType.KINESIS_FIREHOSE,
    ServiceType.MSK,
    ServiceType.OPENSEARCH,
    ServiceType.REDSHIFT,
    ServiceType.QUICKSIGHT,
    ServiceType.LAKE_FORMATION,
    ServiceType.DATAZONE,
    ServiceType.CONNECT,
    ServiceType.SES,
    ServiceType.PINPOINT,
    ServiceType.AURORA,
    ServiceType.DOCUMENTDB,
    ServiceType.ELASTICACHE,
    ServiceType.NEPTUNE,
    ServiceType.RDS,
    ServiceType.TIMESTREAM,
    ServiceType.DATABASE_MIGRATION_SERVICE,
    ServiceType.KEYSPACES,
    ServiceType.MEMORYDB,
    ServiceType.CODEARTIFACT,
    ServiceType.X_RAY,
    ServiceType.CODEBUILD,
    ServiceType.CODECOMMIT,
    ServiceType.CODEDEPLOY,
    ServiceType.CODEPIPELINE,
    ServiceType.APPSTREAM,
    ServiceType.AMPLIFY,
    ServiceType.GAMELIFT,
]

# The 63 icon-only service types
ICON_ONLY_SERVICES = [
    # Analytics icon-only (12)
    ServiceType.CLEAN_ROOMS,
    ServiceType.DATA_EXCHANGE,
    ServiceType.DATA_PIPELINE,
    ServiceType.FINSPACE,
    ServiceType.GLUE_DATABREW,
    ServiceType.GLUE_ELASTIC_VIEWS,
    ServiceType.KINESIS_DATA_ANALYTICS,
    ServiceType.KINESIS_DATA_STREAMS,
    ServiceType.KINESIS_VIDEO_STREAMS,
    # Blockchain icon-only (2)
    ServiceType.MANAGED_BLOCKCHAIN,
    ServiceType.QUANTUM_LEDGER_DATABASE,
    # Business Applications icon-only (11)
    ServiceType.ALEXA_FOR_BUSINESS,
    ServiceType.CHIME_SDK,
    ServiceType.CHIME_VOICE_CONNECTOR,
    ServiceType.CHIME,
    ServiceType.HONEYCODE,
    ServiceType.PINPOINT_APIS,
    ServiceType.SUPPLY_CHAIN,
    ServiceType.WICKR,
    ServiceType.WORKDOCS_SDK,
    ServiceType.WORKDOCS,
    ServiceType.WORKMAIL,
    # Cloud Financial Management icon-only (7)
    ServiceType.APPLICATION_COST_PROFILER,
    ServiceType.BILLING_CONDUCTOR,
    ServiceType.BUDGETS,
    ServiceType.COST_AND_USAGE_REPORT,
    ServiceType.COST_EXPLORER,
    ServiceType.RESERVED_INSTANCE_REPORTING,
    ServiceType.SAVINGS_PLANS,
    # Customer Enablement icon-only (7)
    ServiceType.ACTIVATE,
    ServiceType.IQ,
    ServiceType.MANAGED_SERVICES,
    ServiceType.PROFESSIONAL_SERVICES,
    ServiceType.REPOST,
    ServiceType.SUPPORT,
    ServiceType.TRAINING_CERTIFICATION,
    # Database icon-only
    ServiceType.RDS_ON_VMWARE,
    # Developer Tools icon-only (12)
    ServiceType.APPLICATION_COMPOSER,
    ServiceType.CLOUD_CONTROL_API,
    ServiceType.CLOUD_DEVELOPMENT_KIT,
    ServiceType.CLOUD9,
    ServiceType.CLOUDSHELL,
    ServiceType.CODECATALYST,
    ServiceType.CODESTAR,
    ServiceType.COMMAND_LINE_INTERFACE,
    ServiceType.CORRETTO,
    ServiceType.TOOLS_AND_SDKS,
    # End User Computing icon-only (2)
    ServiceType.WORKLINK,
    ServiceType.WORKSPACES_FAMILY,
    # Front End Web Mobile icon-only (2)
    ServiceType.DEVICE_FARM,
    ServiceType.LOCATION_SERVICE,
    # Games icon-only (4)
    ServiceType.GAMEKIT,
    ServiceType.GAMESPARKS,
    ServiceType.LUMBERYARD,
    ServiceType.OPEN_3D_ENGINE,
]


def _minimal_config_for(service_type: ServiceType) -> BaseServiceConfig:
    """Return a minimal config that produces non-empty generator output.

    Most generators produce output from a bare config, but some
    have purely conditional fields. For those, provide at least one value.
    Migrated services use their typed config class.
    """
    from app.models.input_models._general import get_service_config_models

    config_models = get_service_config_models()
    config_cls = config_models.get(service_type)

    # Use typed config if the model has TerraformField annotations
    if config_cls is not None and config_cls.has_terraform_schema():
        # Some typed configs have required fields — provide minimal values
        if service_type == ServiceType.LAMBDA:
            return config_cls(function_name="test-func")
        if service_type == ServiceType.DYNAMODB:
            return config_cls(table_name="test-table", hash_key="id", hash_key_type="S")
        if service_type == ServiceType.API_GATEWAY:
            return config_cls(api_name="test-api", protocol_type="HTTP")
        # Connect needs at least one field set to produce non-empty variables_tf
        if service_type == ServiceType.CONNECT:
            return config_cls(identity_management_type="CONNECT_MANAGED")
        return config_cls()

    # Legacy services still using BaseServiceConfig fallback
    if service_type == ServiceType.CONNECT:
        return BaseServiceConfig(connect_identity_management_type="CONNECT_MANAGED")
    return BaseServiceConfig()


def _make_instance(
    name: str, service_type: ServiceType, config: BaseServiceConfig
) -> ResourceInstanceIR:
    return ResourceInstanceIR(name=name, service_type=service_type, config=config)


# ---------------------------------------------------------------------------
# Property 1: Generator protocol compliance and non-empty output
# ---------------------------------------------------------------------------


@given(
    service_type=st.sampled_from(list(GENERATOR_REGISTRY.keys())),
    name=_resource_name_st,
)
@settings(max_examples=100)
def test_property_1_generator_protocol_compliance_and_non_empty_output(
    service_type, name
):
    """Property 1: For any service type in GENERATOR_REGISTRY, the generator
    produces non-empty strings from generate_resource_tf, generate_variables_tf,
    and generate_outputs_tf when given a valid ResourceInstanceIR.
    """
    config = _minimal_config_for(service_type)
    instance = _make_instance(name, service_type, config)
    generator = GENERATOR_REGISTRY[service_type]

    resource_tf = generator.generate_resource_tf(instance)
    variables_tf = generator.generate_variables_tf(instance)
    outputs_tf = generator.generate_outputs_tf(instance)

    assert isinstance(resource_tf, str) and len(resource_tf) > 0, (
        f"generate_resource_tf returned empty for {service_type.value}"
    )
    assert isinstance(variables_tf, str) and len(variables_tf) > 0, (
        f"generate_variables_tf returned empty for {service_type.value}"
    )
    assert isinstance(outputs_tf, str) and len(outputs_tf) > 0, (
        f"generate_outputs_tf returned empty for {service_type.value}"
    )


# ---------------------------------------------------------------------------
# Property 2: Conditional config field inclusion
# ---------------------------------------------------------------------------

# Mapping: service_type -> list of (config_field_name, expected_var_reference)
# Only services with optional config fields are included.
OPTIONAL_FIELD_MAP: dict[ServiceType, list[tuple[str, str]]] = {
    ServiceType.EMR: [
        ("release_label", "var.release_label"),
        ("service_role", "var.service_role"),
    ],
    ServiceType.KINESIS: [
        ("shard_count", "var.shard_count"),
    ],
    ServiceType.KINESIS_FIREHOSE: [
        ("destination", "var.destination"),
    ],
    ServiceType.MSK: [
        ("kafka_version", "var.kafka_version"),
        ("number_of_broker_nodes", "var.number_of_broker_nodes"),
    ],
    ServiceType.REDSHIFT: [
        ("node_type", "var.node_type"),
        ("master_username", "var.master_username"),
    ],
    ServiceType.CONNECT: [
        ("identity_management_type", "var.identity_management_type"),
        ("inbound_calls_enabled", "var.inbound_calls_enabled"),
        ("outbound_calls_enabled", "var.outbound_calls_enabled"),
    ],
    ServiceType.AURORA: [
        ("engine", "var.engine"),
        ("master_username", "var.master_username"),
    ],
    ServiceType.DOCUMENTDB: [
        ("master_username", "var.master_username"),
    ],
    ServiceType.ELASTICACHE: [
        ("engine", "var.engine"),
        ("node_type", "var.node_type"),
        ("num_cache_nodes", "var.num_cache_nodes"),
    ],
    ServiceType.RDS: [
        ("engine", "var.engine"),
        ("instance_class", "var.instance_class"),
        ("allocated_storage", "var.allocated_storage"),
        ("username", "var.username"),
    ],
    ServiceType.CODEBUILD: [
        ("source_type", "var.source_type"),
        ("service_role", "var.service_role"),
    ],
    ServiceType.CODEDEPLOY: [
        ("compute_platform", "var.compute_platform"),
    ],
    ServiceType.CODEPIPELINE: [
        ("role_arn", "var.role_arn"),
    ],
    ServiceType.APPSTREAM: [
        ("instance_type", "var.instance_type"),
    ],
    ServiceType.GAMELIFT: [
        ("ec2_instance_type", "var.ec2_instance_type"),
    ],
}

# Services that have optional fields (used for sampling)
_SERVICES_WITH_OPTIONAL_FIELDS = list(OPTIONAL_FIELD_MAP.keys())

# Sample values for optional config fields by type
_OPTIONAL_FIELD_VALUES: dict[str, object] = {
    "release_label": "emr-6.10.0",
    "shard_count": 2,
    "destination": "s3",
    "kafka_version": "3.5.1",
    "number_of_broker_nodes": 3,
    "node_type": "dc2.large",
    "master_username": "admin",
    "identity_management_type": "SAML",
    "inbound_calls_enabled": True,
    "outbound_calls_enabled": True,
    "engine": "aurora-mysql",
    "num_cache_nodes": 1,
    "instance_class": "db.t3.micro",
    "allocated_storage": 20,
    "username": "admin",
    "source_type": "CODECOMMIT",
    "service_role": "arn:aws:iam::123456789012:role/codebuild-role",
    "compute_platform": "Server",
    "role_arn": "arn:aws:iam::123456789012:role/pipeline-role",
    "instance_type": "stream.standard.medium",
    "ec2_instance_type": "c5.large",
}


@st.composite
def _config_with_random_optional_fields(draw):
    """Generate a (ServiceType, config, set_fields, unset_fields) tuple.

    For a randomly chosen service with optional fields, randomly set/unset
    each optional field. Uses typed config models for migrated database services.
    """
    service_type = draw(st.sampled_from(_SERVICES_WITH_OPTIONAL_FIELDS))
    fields = OPTIONAL_FIELD_MAP[service_type]

    # Generate a bitmask for which fields to set (at least one combination)
    flags = draw(
        st.lists(
            st.booleans(),
            min_size=len(fields),
            max_size=len(fields),
        )
    )

    config_kwargs: dict = {}
    set_fields: list[tuple[str, str]] = []
    unset_fields: list[tuple[str, str]] = []

    for (field_name, var_ref), should_set in zip(fields, flags, strict=True):
        if should_set:
            config_kwargs[field_name] = _OPTIONAL_FIELD_VALUES[field_name]
            set_fields.append((field_name, var_ref))
        else:
            # Explicitly set to None so fields with non-None defaults are cleared
            config_kwargs[field_name] = None
            unset_fields.append((field_name, var_ref))

    if service_type in _TYPED_CONFIG_CLASSES:
        config = _TYPED_CONFIG_CLASSES[service_type](**config_kwargs)
    else:
        config = BaseServiceConfig(**config_kwargs)
    return service_type, config, set_fields, unset_fields


@given(
    data=_config_with_random_optional_fields(),
    name=_resource_name_st,
)
@settings(max_examples=100)
def test_property_2_conditional_config_field_inclusion(data, name):
    """Property 2: When an optional config field is None, its var reference
    does NOT appear in resource_tf output. When set, it DOES appear.
    """
    service_type, config, set_fields, unset_fields = data
    instance = _make_instance(name, service_type, config)
    generator = GENERATOR_REGISTRY[service_type]
    resource_tf = generator.generate_resource_tf(instance)

    for field_name, var_ref in set_fields:
        assert var_ref in resource_tf, (
            f"Expected '{var_ref}' in resource_tf for {service_type.value} "
            f"when {field_name} is set, but not found.\nHCL:\n{resource_tf}"
        )

    for field_name, var_ref in unset_fields:
        assert var_ref not in resource_tf, (
            f"Expected '{var_ref}' NOT in resource_tf for {service_type.value} "
            f"when {field_name} is None, but it was found.\nHCL:\n{resource_tf}"
        )


# ---------------------------------------------------------------------------
# Property 3: Required Terraform blocks per service
# ---------------------------------------------------------------------------

# Expected blocks per service: (resource_type_strings, variable_names, output_names)
EXPECTED_BLOCKS: dict[ServiceType, tuple[list[str], list[str], list[str]]] = {
    ServiceType.QUICKSIGHT: (
        ['resource "aws_quicksight_namespace"'],
        ["namespace_name", "aws_account_id", "identity_store"],
        ["namespace_arn", "namespace_name"],
    ),
    ServiceType.LAKE_FORMATION: (
        ['resource "aws_lakeformation_resource"'],
        ["resource_arn", "use_service_linked_role"],
        ["resource_arn"],
    ),
    ServiceType.DATAZONE: (
        ['resource "aws_datazone_domain"'],
        ["domain_name", "domain_execution_role"],
        ["domain_id", "domain_arn"],
    ),
    ServiceType.CODEARTIFACT: (
        [
            'resource "aws_codeartifact_domain"',
            'resource "aws_codeartifact_repository"',
        ],
        ["domain_name", "repository_name"],
        ["domain_arn", "repository_arn"],
    ),
    ServiceType.X_RAY: (
        ['resource "aws_xray_group"'],
        ["group_name", "filter_expression"],
        ["group_arn", "group_name"],
    ),
    ServiceType.DATABASE_MIGRATION_SERVICE: (
        ['resource "aws_dms_replication_instance"'],
        ["replication_instance_id", "replication_instance_class"],
        ["replication_instance_arn", "replication_instance_id"],
    ),
    ServiceType.KEYSPACES: (
        ['resource "aws_keyspaces_keyspace"'],
        ["keyspace_name"],
        ["keyspace_id", "keyspace_arn"],
    ),
    ServiceType.MEMORYDB: (
        ['resource "aws_memorydb_cluster"'],
        ["cluster_name", "node_type", "acl_name"],
        ["cluster_arn", "cluster_endpoint"],
    ),
    ServiceType.ATHENA: (
        ['resource "aws_athena_workgroup"'],
        ["workgroup_name"],
        ["workgroup_arn", "workgroup_name"],
    ),
    ServiceType.CLOUDSEARCH: (
        ['resource "aws_cloudsearch_domain"'],
        ["domain_name"],
        ["domain_arn", "domain_id"],
    ),
    ServiceType.EMR: (
        ['resource "aws_emr_cluster"'],
        ["cluster_name"],
        ["cluster_id", "cluster_arn"],
    ),
    ServiceType.GLUE: (
        ['resource "aws_glue_catalog_database"'],
        ["database_name"],
        ["database_name", "catalog_id"],
    ),
    ServiceType.KINESIS: (
        ['resource "aws_kinesis_stream"'],
        ["stream_name"],
        ["stream_arn", "stream_name"],
    ),
    ServiceType.KINESIS_FIREHOSE: (
        ['resource "aws_kinesis_firehose_delivery_stream"'],
        ["stream_name"],
        ["delivery_stream_arn", "delivery_stream_name"],
    ),
    ServiceType.MSK: (
        ['resource "aws_msk_cluster"'],
        ["cluster_name"],
        ["cluster_arn", "bootstrap_brokers"],
    ),
    ServiceType.OPENSEARCH: (
        ['resource "aws_opensearch_domain"'],
        ["domain_name"],
        ["domain_arn", "domain_endpoint"],
    ),
    ServiceType.REDSHIFT: (
        ['resource "aws_redshift_cluster"'],
        ["cluster_identifier"],
        ["cluster_arn", "cluster_endpoint"],
    ),
    ServiceType.CONNECT: (
        ['resource "aws_connect_instance"'],
        [],
        ["instance_id", "instance_arn"],
    ),
    ServiceType.SES: (
        ['resource "aws_ses_domain_identity"'],
        ["domain"],
        ["domain_arn", "verification_token"],
    ),
    ServiceType.PINPOINT: (
        ['resource "aws_pinpoint_app"'],
        ["app_name"],
        ["application_id", "app_arn"],
    ),
    ServiceType.AURORA: (
        ['resource "aws_rds_cluster"'],
        ["cluster_identifier"],
        ["cluster_arn", "cluster_endpoint"],
    ),
    ServiceType.DOCUMENTDB: (
        ['resource "aws_docdb_cluster"'],
        ["cluster_identifier"],
        ["cluster_arn", "cluster_endpoint"],
    ),
    ServiceType.ELASTICACHE: (
        ['resource "aws_elasticache_cluster"'],
        ["cluster_id"],
        ["cluster_arn", "cache_nodes"],
    ),
    ServiceType.NEPTUNE: (
        ['resource "aws_neptune_cluster"'],
        ["cluster_identifier"],
        ["cluster_arn", "cluster_endpoint"],
    ),
    ServiceType.RDS: (
        ['resource "aws_db_instance"'],
        ["db_identifier"],
        ["db_instance_arn", "db_instance_endpoint"],
    ),
    ServiceType.TIMESTREAM: (
        ['resource "aws_timestreamwrite_database"'],
        ["database_name"],
        ["database_arn", "database_name"],
    ),
    ServiceType.CODEBUILD: (
        ['resource "aws_codebuild_project"'],
        ["project_name"],
        ["project_arn", "project_name"],
    ),
    ServiceType.CODECOMMIT: (
        ['resource "aws_codecommit_repository"'],
        ["repository_name"],
        ["repository_arn", "clone_url_http"],
    ),
    ServiceType.CODEDEPLOY: (
        ['resource "aws_codedeploy_app"'],
        ["app_name"],
        ["app_id", "app_name"],
    ),
    ServiceType.CODEPIPELINE: (
        ['resource "aws_codepipeline"'],
        ["pipeline_name"],
        ["pipeline_arn", "pipeline_name"],
    ),
    ServiceType.APPSTREAM: (
        ['resource "aws_appstream_fleet"'],
        ["fleet_name"],
        ["fleet_arn", "fleet_name"],
    ),
    ServiceType.AMPLIFY: (
        ['resource "aws_amplify_app"'],
        ["app_name"],
        ["app_id", "app_arn"],
    ),
    ServiceType.GAMELIFT: (
        ['resource "aws_gamelift_fleet"'],
        ["fleet_name"],
        ["fleet_arn", "fleet_id"],
    ),
}


@given(
    service_type=st.sampled_from(FULL_GENERATOR_SERVICES),
    name=_resource_name_st,
)
@settings(max_examples=100)
def test_property_3_required_terraform_blocks_per_service(service_type, name):
    """Property 3: For each full-generator service, the output contains all
    expected resource type strings, variable block names, and output block names.
    """
    config = _minimal_config_for(service_type)
    instance = _make_instance(name, service_type, config)
    generator = GENERATOR_REGISTRY[service_type]

    resource_tf = generator.generate_resource_tf(instance)
    variables_tf = generator.generate_variables_tf(instance)
    outputs_tf = generator.generate_outputs_tf(instance)

    expected_resources, expected_vars, expected_outputs = EXPECTED_BLOCKS[service_type]

    for res_str in expected_resources:
        assert res_str in resource_tf, (
            f"Expected '{res_str}' in resource_tf for {service_type.value}.\n"
            f"HCL:\n{resource_tf}"
        )

    for var_name in expected_vars:
        assert f'variable "{var_name}"' in variables_tf, (
            f"Expected 'variable \"{var_name}\"' in variables_tf for {service_type.value}.\n"
            f"HCL:\n{variables_tf}"
        )

    for out_name in expected_outputs:
        assert f'output "{out_name}"' in outputs_tf, (
            f"Expected 'output \"{out_name}\"' in outputs_tf for {service_type.value}.\n"
            f"HCL:\n{outputs_tf}"
        )


# ---------------------------------------------------------------------------
# Property 4: Icon-only services excluded from generator registry
# ---------------------------------------------------------------------------


@given(service_type=st.sampled_from(ICON_ONLY_SERVICES))
@settings(max_examples=100)
def test_property_4_icon_only_services_excluded_from_registry(service_type):
    """Property 4: No icon-only service type has an entry in GENERATOR_REGISTRY."""
    assert service_type not in GENERATOR_REGISTRY, (
        f"Icon-only service {service_type.value} should NOT be in GENERATOR_REGISTRY"
    )


# ---------------------------------------------------------------------------
# Property 5: Pipeline skip behavior for mixed service types
# ---------------------------------------------------------------------------


@st.composite
def _mixed_project_ir(draw):
    """Generate a ProjectIR with a mix of full-generator and icon-only resources.

    Ensures at least one full-generator and at least one icon-only resource.
    """
    # Pick 1-3 full-generator services
    full_services = draw(
        st.lists(
            st.sampled_from(FULL_GENERATOR_SERVICES),
            min_size=1,
            max_size=3,
            unique=True,
        )
    )
    # Pick 1-3 icon-only services
    icon_services = draw(
        st.lists(
            st.sampled_from(ICON_ONLY_SERVICES),
            min_size=1,
            max_size=3,
            unique=True,
        )
    )

    all_services = full_services + icon_services
    modules = []
    all_module_refs = []

    for i, svc in enumerate(all_services):
        inst_name = draw(_resource_name_st)
        # Ensure unique names by appending index
        inst_name = f"{inst_name}{i}"
        config = _minimal_config_for(svc)
        instance = ResourceInstanceIR(
            name=inst_name,
            service_type=svc,
            config=config,
        )
        modules.append(ServiceModuleIR(service_type=svc, instances=[instance]))
        all_module_refs.append(svc)

    project_name = draw(st.from_regex(r"[a-z][a-z0-9\-]{2,14}", fullmatch=True))

    return ProjectIR(
        project_name=project_name,
        environments=[
            EnvironmentIR(name="dev", variables={}, module_refs=all_module_refs),
        ],
        modules=modules,
        connections=[],
    )


@given(project=_mixed_project_ir())
@settings(max_examples=100)
def test_property_5_pipeline_skip_behavior_for_mixed_service_types(project):
    """Property 5: FileTreeAssembler produces module files only for full-generator
    resources and no files for icon-only resources, without raising errors.
    """
    assembler = FileTreeAssembler()
    file_tree = assembler.assemble(project)

    for module in project.modules:
        stype_name = module.service_type.value
        category = get_category(module.service_type)
        module_prefix = f"{project.project_name}/modules/{category}/{stype_name}/"

        module_files = [p for p in file_tree if p.startswith(module_prefix)]

        if module.service_type in GENERATOR_REGISTRY:
            # Full-generator service: should have module files
            assert len(module_files) > 0, (
                f"Expected module files for full-generator service {stype_name}, "
                f"but found none in file tree."
            )
        else:
            # Icon-only service: should have NO module files
            assert len(module_files) == 0, (
                f"Expected NO module files for icon-only service {stype_name}, "
                f"but found: {module_files}"
            )
