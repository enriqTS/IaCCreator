"""Input data models (Pydantic schemas) for the Terraform IaC Generator."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ServiceType(str, Enum):
    """Supported AWS service types."""

    LAMBDA = "lambda"
    S3 = "s3"
    API_GATEWAY = "api-gateway"
    DYNAMODB = "dynamodb"
    IAM = "iam"
    CLOUDWATCH = "cloudwatch"
    SNS = "sns"
    SQS = "sqs"

    # Compute – full-generator services
    EC2 = "ec2"
    ECS = "ecs"
    EKS = "eks"
    ELASTIC_BEANSTALK = "elastic-beanstalk"
    APP_RUNNER = "app-runner"
    BATCH = "batch"
    EC2_IMAGE_BUILDER = "ec2-image-builder"
    LIGHTSAIL = "lightsail"
    ECR = "ecr"

    # Compute – icon-only services
    APPLICATION_AUTO_SCALING = "application-auto-scaling"
    BOTTLEROCKET = "bottlerocket"
    COMPUTE_OPTIMIZER = "compute-optimizer"
    EC2_AUTO_SCALING = "ec2-auto-scaling"
    ELASTIC_FABRIC_ADAPTER = "elastic-fabric-adapter"
    FARGATE = "fargate"
    GENOMICS_CLI = "genomics-cli"
    LOCAL_ZONES = "local-zones"
    NICE_DCV = "nice-dcv"
    NICE_ENGINFRAME = "nice-enginframe"
    NITRO_ENCLAVES = "nitro-enclaves"
    OUTPOSTS_FAMILY = "outposts-family"
    OUTPOSTS_RACK = "outposts-rack"
    OUTPOSTS_SERVERS = "outposts-servers"
    PARALLELCLUSTER = "parallelcluster"
    SERVERLESS_APPLICATION_REPOSITORY = "serverless-application-repository"
    SIMSPACE_WEAVER = "simspace-weaver"
    THINKBOX_DEADLINE = "thinkbox-deadline"
    THINKBOX_FROST = "thinkbox-frost"
    THINKBOX_KRAKATOA = "thinkbox-krakatoa"
    THINKBOX_SEQUOIA = "thinkbox-sequoia"
    THINKBOX_STOKE = "thinkbox-stoke"
    THINKBOX_XMESH = "thinkbox-xmesh"
    VMWARE_CLOUD_ON_AWS = "vmware-cloud-on-aws"
    WAVELENGTH = "wavelength"

    # Containers – icon-only services
    ECS_ANYWHERE = "ecs-anywhere"
    EKS_ANYWHERE = "eks-anywhere"
    EKS_CLOUD = "eks-cloud"
    EKS_DISTRO = "eks-distro"
    RED_HAT_OPENSHIFT = "red-hat-openshift"

    # Analytics – full-generator services
    ATHENA = "athena"
    CLOUDSEARCH = "cloudsearch"
    EMR = "emr"
    GLUE = "glue"
    KINESIS = "kinesis"
    KINESIS_FIREHOSE = "kinesis-firehose"
    MSK = "msk"
    OPENSEARCH = "opensearch"
    REDSHIFT = "redshift"

    # Business Applications – full-generator services
    CONNECT = "connect"
    SES = "ses"
    PINPOINT = "pinpoint"

    # Database – full-generator services
    AURORA = "aurora"
    DOCUMENTDB = "documentdb"
    ELASTICACHE = "elasticache"
    NEPTUNE = "neptune"
    RDS = "rds"
    TIMESTREAM = "timestream"

    # Developer Tools – full-generator services
    CODEBUILD = "codebuild"
    CODECOMMIT = "codecommit"
    CODEDEPLOY = "codedeploy"
    CODEPIPELINE = "codepipeline"

    # End User Computing – full-generator services
    APPSTREAM = "appstream"

    # Front End Web Mobile – full-generator services
    AMPLIFY = "amplify"

    # Games – full-generator services
    GAMELIFT = "gamelift"

    # Analytics – icon-only services
    CLEAN_ROOMS = "clean-rooms"
    DATA_EXCHANGE = "data-exchange"
    DATA_PIPELINE = "data-pipeline"
    DATAZONE = "datazone"
    FINSPACE = "finspace"
    GLUE_DATABREW = "glue-databrew"
    GLUE_ELASTIC_VIEWS = "glue-elastic-views"
    KINESIS_DATA_ANALYTICS = "kinesis-data-analytics"
    KINESIS_DATA_STREAMS = "kinesis-data-streams"
    KINESIS_VIDEO_STREAMS = "kinesis-video-streams"
    LAKE_FORMATION = "lake-formation"
    QUICKSIGHT = "quicksight"

    # Blockchain – icon-only services
    MANAGED_BLOCKCHAIN = "managed-blockchain"
    QUANTUM_LEDGER_DATABASE = "quantum-ledger-database"

    # Business Applications – icon-only services
    ALEXA_FOR_BUSINESS = "alexa-for-business"
    CHIME_SDK = "chime-sdk"
    CHIME_VOICE_CONNECTOR = "chime-voice-connector"
    CHIME = "chime"
    HONEYCODE = "honeycode"
    PINPOINT_APIS = "pinpoint-apis"
    SUPPLY_CHAIN = "supply-chain"
    WICKR = "wickr"
    WORKDOCS_SDK = "workdocs-sdk"
    WORKDOCS = "workdocs"
    WORKMAIL = "workmail"

    # Cloud Financial Management – icon-only services
    APPLICATION_COST_PROFILER = "application-cost-profiler"
    BILLING_CONDUCTOR = "billing-conductor"
    BUDGETS = "budgets"
    COST_AND_USAGE_REPORT = "cost-and-usage-report"
    COST_EXPLORER = "cost-explorer"
    RESERVED_INSTANCE_REPORTING = "reserved-instance-reporting"
    SAVINGS_PLANS = "savings-plans"

    # Customer Enablement – icon-only services
    ACTIVATE = "activate"
    IQ = "iq"
    MANAGED_SERVICES = "managed-services"
    PROFESSIONAL_SERVICES = "professional-services"
    REPOST = "repost"
    SUPPORT = "support"
    TRAINING_CERTIFICATION = "training-certification"

    # Database – icon-only services
    DATABASE_MIGRATION_SERVICE = "database-migration-service"
    KEYSPACES = "keyspaces"
    MEMORYDB = "memorydb"
    RDS_ON_VMWARE = "rds-on-vmware"

    # Developer Tools – icon-only services
    APPLICATION_COMPOSER = "application-composer"
    CLOUD_CONTROL_API = "cloud-control-api"
    CLOUD_DEVELOPMENT_KIT = "cloud-development-kit"
    CLOUD9 = "cloud9"
    CLOUDSHELL = "cloudshell"
    CODEARTIFACT = "codeartifact"
    CODECATALYST = "codecatalyst"
    CODESTAR = "codestar"
    COMMAND_LINE_INTERFACE = "command-line-interface"
    CORRETTO = "corretto"
    TOOLS_AND_SDKS = "tools-and-sdks"
    X_RAY = "x-ray"

    # End User Computing – icon-only services
    WORKLINK = "worklink"
    WORKSPACES_FAMILY = "workspaces-family"

    # Front End Web Mobile – icon-only services
    DEVICE_FARM = "device-farm"
    LOCATION_SERVICE = "location-service"

    # Games – icon-only services
    GAMEKIT = "gamekit"
    GAMESPARKS = "gamesparks"
    LUMBERYARD = "lumberyard"
    OPEN_3D_ENGINE = "open-3d-engine"


class ResourceConfig(BaseModel):
    """Service-specific configuration for a resource instance."""

    # Lambda
    handler: Optional[str] = None
    runtime: Optional[str] = None
    memory_size: Optional[int] = None
    timeout: Optional[int] = None
    is_layer: bool = False
    description: Optional[str] = None
    environment_variables: Optional[dict[str, str]] = None
    tags: Optional[dict[str, str]] = None
    layers: Optional[list[str]] = None
    architectures: Optional[str] = None
    ephemeral_storage_size: Optional[int] = None
    reserved_concurrent_executions: Optional[int] = None
    publish: Optional[bool] = None
    # S3
    versioning: Optional[bool] = None
    force_destroy: Optional[bool] = None
    object_lock_enabled: Optional[bool] = None
    acceleration_status: Optional[str] = None
    # DynamoDB
    billing_mode: Optional[str] = None
    hash_key: Optional[str] = None
    hash_key_type: Optional[str] = None
    range_key: Optional[str] = None
    range_key_type: Optional[str] = None
    read_capacity: Optional[int] = None
    write_capacity: Optional[int] = None
    point_in_time_recovery_enabled: Optional[bool] = None
    deletion_protection_enabled: Optional[bool] = None
    table_class: Optional[str] = None
    # API Gateway
    protocol_type: Optional[str] = None
    cors_configuration: Optional[dict] = None
    disable_execute_api_endpoint: Optional[bool] = None
    route_selection_expression: Optional[str] = None
    # API Gateway — new fields
    routes: Optional[list[dict]] = None
    stages: Optional[list[dict]] = None
    authorizers: Optional[list[dict]] = None
    custom_domain: Optional[dict] = None
    vpc_links: Optional[list[dict]] = None
    integrations: Optional[list[dict]] = None
    api_key_required: Optional[bool] = None
    throttling_burst_limit: Optional[int] = None
    throttling_rate_limit: Optional[float] = None
    access_log_retention_days: Optional[int] = None
    access_log_format: Optional[str] = None
    # CloudWatch
    retention_in_days: Optional[int] = None
    kms_key_id: Optional[str] = None
    log_group_class: Optional[str] = None
    # SNS
    display_name: Optional[str] = None
    fifo_topic: Optional[bool] = None
    content_based_deduplication: Optional[bool] = None  # shared with SQS
    kms_master_key_id: Optional[str] = None  # shared with CloudWatch
    # SQS
    visibility_timeout_seconds: Optional[int] = None
    message_retention_seconds: Optional[int] = None
    fifo_queue: Optional[bool] = None
    delay_seconds: Optional[int] = None
    max_message_size: Optional[int] = None
    # EC2
    instance_type: Optional[str] = None
    ami: Optional[str] = None
    key_name: Optional[str] = None
    # ECS
    ecs_launch_type: Optional[str] = None
    ecs_desired_count: Optional[int] = None
    ecs_cpu: Optional[str] = None
    ecs_memory: Optional[str] = None
    # EKS
    eks_version: Optional[str] = None
    eks_endpoint_public_access: Optional[bool] = None
    # Elastic Beanstalk
    eb_solution_stack_name: Optional[str] = None
    eb_tier: Optional[str] = None
    # App Runner
    apprunner_source_type: Optional[str] = None
    apprunner_image_identifier: Optional[str] = None
    # Batch
    batch_compute_environment_type: Optional[str] = None
    batch_max_vcpus: Optional[int] = None
    # EC2 Image Builder
    imagebuilder_image_recipe_arn: Optional[str] = None
    imagebuilder_infrastructure_configuration_arn: Optional[str] = None
    # Lightsail
    lightsail_blueprint_id: Optional[str] = None
    lightsail_bundle_id: Optional[str] = None
    lightsail_availability_zone: Optional[str] = None
    # ECR
    ecr_image_tag_mutability: Optional[str] = None
    ecr_scan_on_push: Optional[bool] = None
    # Analytics
    athena_name: Optional[str] = None
    cloudsearch_name: Optional[str] = None
    emr_release_label: Optional[str] = None
    emr_service_role: Optional[str] = None
    glue_catalog_database_name: Optional[str] = None
    kinesis_shard_count: Optional[int] = None
    firehose_destination: Optional[str] = None
    msk_kafka_version: Optional[str] = None
    msk_number_of_broker_nodes: Optional[int] = None
    opensearch_domain_name: Optional[str] = None
    redshift_node_type: Optional[str] = None
    redshift_master_username: Optional[str] = None
    # Business Applications
    connect_identity_management_type: Optional[str] = None
    connect_inbound_calls_enabled: Optional[bool] = None
    connect_outbound_calls_enabled: Optional[bool] = None
    ses_domain: Optional[str] = None
    pinpoint_name: Optional[str] = None
    # Database
    aurora_engine: Optional[str] = None
    aurora_master_username: Optional[str] = None
    documentdb_master_username: Optional[str] = None
    elasticache_engine: Optional[str] = None
    elasticache_node_type: Optional[str] = None
    elasticache_num_cache_nodes: Optional[int] = None
    neptune_cluster_identifier: Optional[str] = None
    rds_engine: Optional[str] = None
    rds_instance_class: Optional[str] = None
    rds_allocated_storage: Optional[int] = None
    rds_username: Optional[str] = None
    timestream_database_name: Optional[str] = None
    # Developer Tools
    codebuild_source_type: Optional[str] = None
    codebuild_service_role: Optional[str] = None
    codecommit_repository_name: Optional[str] = None
    codedeploy_compute_platform: Optional[str] = None
    codepipeline_role_arn: Optional[str] = None
    # End User Computing
    appstream_instance_type: Optional[str] = None
    # Front End Web Mobile
    amplify_name: Optional[str] = None
    # Games
    gamelift_ec2_instance_type: Optional[str] = None


class ResourceInstance(BaseModel):
    """A specific named resource within a service module."""

    name: str = Field(..., description="User-defined resource name, used as subfolder name")
    service_type: ServiceType
    config: ResourceConfig = Field(default_factory=ResourceConfig)
    terraform_variables: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dynamodb_hash_key(self) -> "ResourceInstance":
        """DynamoDB resources must have hash_key in config."""
        if self.service_type == ServiceType.DYNAMODB and self.config.hash_key is None:
            raise ValueError(
                "DynamoDB resource must have 'hash_key' specified in config"
            )
        return self


class Connection(BaseModel):
    """A connection between two resource instances."""

    source: str = Field(..., description="Name of the source resource instance")
    target: str = Field(..., description="Name of the target resource instance")
    connection_type: str = Field(
        ..., description="e.g., 'triggers', 'reads_from', 'writes_to'"
    )
    connection_config: dict[str, str | int | float | bool] = Field(default_factory=dict)


class EnvironmentConfig(BaseModel):
    """Configuration for a deployment environment."""

    name: str = Field(..., description="Environment name, e.g., dev, staging, prod")
    variables: dict[str, str] = Field(default_factory=dict)


class GlobalTerraformConfig(BaseModel):
    """Project-level Terraform configuration for backend, provider, and version constraints."""

    backend_type: str = "local"
    backend_config: dict[str, str] = Field(default_factory=dict)
    provider_region: str = "us-east-1"
    provider_profile: str | None = None
    terraform_version: str | None = None
    aws_provider_version: str | None = None


class ArchitectureDescription(BaseModel):
    """Top-level input schema for the Terraform IaC Generator."""

    project_name: str = Field(
        ..., description="Root folder name for the generated project"
    )
    environments: list[EnvironmentConfig] = Field(..., min_length=1)
    resources: list[ResourceInstance] = Field(..., min_length=1)
    connections: list[Connection] = Field(default_factory=list)
    global_terraform_config: GlobalTerraformConfig = Field(default_factory=GlobalTerraformConfig)
