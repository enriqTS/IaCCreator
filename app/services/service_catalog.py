"""Backend-owned capabilities and classification for AWS service types."""

from dataclasses import dataclass

from app.generators.registry import GENERATOR_REGISTRY
from app.models.editor_models import (
    ServiceCapabilitiesResponse,
    ServiceClassification,
    ServiceLifecycle,
)
from app.models.input_models import ServiceType, get_service_config_models
from app.services.connection_handlers.registry import CONNECTION_SPECS


@dataclass(frozen=True)
class ServiceMetadata:
    display_name: str
    category: str
    classification: ServiceClassification
    lifecycle: ServiceLifecycle
    capabilities: ServiceCapabilitiesResponse


_CATEGORY_MEMBERS: dict[str, set[ServiceType]] = {
    "analytics": {
        ServiceType.ATHENA,
        ServiceType.CLOUDSEARCH,
        ServiceType.EMR,
        ServiceType.GLUE,
        ServiceType.KINESIS,
        ServiceType.KINESIS_FIREHOSE,
        ServiceType.MSK,
        ServiceType.OPENSEARCH,
        ServiceType.REDSHIFT,
        ServiceType.CLEAN_ROOMS,
        ServiceType.DATA_EXCHANGE,
        ServiceType.DATA_PIPELINE,
        ServiceType.DATAZONE,
        ServiceType.FINSPACE,
        ServiceType.GLUE_DATABREW,
        ServiceType.GLUE_ELASTIC_VIEWS,
        ServiceType.KINESIS_DATA_ANALYTICS,
        ServiceType.KINESIS_DATA_STREAMS,
        ServiceType.LAKE_FORMATION,
        ServiceType.QUICKSIGHT,
    },
    "blockchain": {ServiceType.MANAGED_BLOCKCHAIN, ServiceType.QUANTUM_LEDGER_DATABASE},
    "business-applications": {
        ServiceType.CONNECT,
        ServiceType.SES,
        ServiceType.PINPOINT,
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
    },
    "cloud-financial-management": {
        ServiceType.APPLICATION_COST_PROFILER,
        ServiceType.BILLING_CONDUCTOR,
        ServiceType.BUDGETS,
        ServiceType.COST_AND_USAGE_REPORT,
        ServiceType.COST_EXPLORER,
        ServiceType.RESERVED_INSTANCE_REPORTING,
        ServiceType.SAVINGS_PLANS,
    },
    "compute": {
        ServiceType.LAMBDA,
        ServiceType.EC2,
        ServiceType.ECS,
        ServiceType.EKS,
        ServiceType.ELASTIC_BEANSTALK,
        ServiceType.APP_RUNNER,
        ServiceType.BATCH,
        ServiceType.EC2_IMAGE_BUILDER,
        ServiceType.LIGHTSAIL,
        ServiceType.ECR,
        ServiceType.APPLICATION_AUTO_SCALING,
        ServiceType.BOTTLEROCKET,
        ServiceType.COMPUTE_OPTIMIZER,
        ServiceType.EC2_AUTO_SCALING,
        ServiceType.ELASTIC_FABRIC_ADAPTER,
        ServiceType.FARGATE,
        ServiceType.GENOMICS_CLI,
        ServiceType.LOCAL_ZONES,
        ServiceType.NICE_DCV,
        ServiceType.NICE_ENGINFRAME,
        ServiceType.NITRO_ENCLAVES,
        ServiceType.OUTPOSTS_FAMILY,
        ServiceType.OUTPOSTS_RACK,
        ServiceType.OUTPOSTS_SERVERS,
        ServiceType.PARALLELCLUSTER,
        ServiceType.SERVERLESS_APPLICATION_REPOSITORY,
        ServiceType.SIMSPACE_WEAVER,
        ServiceType.THINKBOX_DEADLINE,
        ServiceType.THINKBOX_FROST,
        ServiceType.THINKBOX_KRAKATOA,
        ServiceType.THINKBOX_SEQUOIA,
        ServiceType.THINKBOX_STOKE,
        ServiceType.THINKBOX_XMESH,
        ServiceType.VMWARE_CLOUD_ON_AWS,
        ServiceType.WAVELENGTH,
    },
    "containers": {
        ServiceType.ECS_ANYWHERE,
        ServiceType.EKS_ANYWHERE,
        ServiceType.EKS_CLOUD,
        ServiceType.EKS_DISTRO,
        ServiceType.RED_HAT_OPENSHIFT,
    },
    "customer-enablement": {
        ServiceType.ACTIVATE,
        ServiceType.IQ,
        ServiceType.MANAGED_SERVICES,
        ServiceType.PROFESSIONAL_SERVICES,
        ServiceType.REPOST,
        ServiceType.SUPPORT,
        ServiceType.TRAINING_CERTIFICATION,
    },
    "database": {
        ServiceType.DYNAMODB,
        ServiceType.AURORA,
        ServiceType.DOCUMENTDB,
        ServiceType.ELASTICACHE,
        ServiceType.NEPTUNE,
        ServiceType.RDS,
        ServiceType.TIMESTREAM,
        ServiceType.DATABASE_MIGRATION_SERVICE,
        ServiceType.KEYSPACES,
        ServiceType.MEMORYDB,
        ServiceType.RDS_ON_VMWARE,
    },
    "developer-tools": {
        ServiceType.CODEBUILD,
        ServiceType.CODECOMMIT,
        ServiceType.CODEDEPLOY,
        ServiceType.CODEPIPELINE,
        ServiceType.APPLICATION_COMPOSER,
        ServiceType.CLOUD_CONTROL_API,
        ServiceType.CLOUD_DEVELOPMENT_KIT,
        ServiceType.CLOUD9,
        ServiceType.CLOUDSHELL,
        ServiceType.CODEARTIFACT,
        ServiceType.CODECATALYST,
        ServiceType.CODESTAR,
        ServiceType.COMMAND_LINE_INTERFACE,
        ServiceType.CORRETTO,
        ServiceType.TOOLS_AND_SDKS,
        ServiceType.X_RAY,
    },
    "end-user-computing": {
        ServiceType.APPSTREAM,
        ServiceType.WORKSPACES,
        ServiceType.WORKLINK,
        ServiceType.WORKSPACES_FAMILY,
    },
    "front-end-web-mobile": {
        ServiceType.AMPLIFY,
        ServiceType.DEVICE_FARM,
        ServiceType.LOCATION_SERVICE,
    },
    "games": {
        ServiceType.GAMELIFT,
        ServiceType.GAMEKIT,
        ServiceType.GAMESPARKS,
        ServiceType.LUMBERYARD,
        ServiceType.OPEN_3D_ENGINE,
    },
    "internet-of-things": {
        ServiceType.IOT_CORE,
        ServiceType.IOT_GREENGRASS,
        ServiceType.IOT_DEVICE_MANAGEMENT,
        ServiceType.IOT_DEVICE_DEFENDER,
        ServiceType.IOT_EVENTS,
        ServiceType.IOT_SITEWISE,
        ServiceType.IOT_TWINMAKER,
        ServiceType.IOT_ANALYTICS,
        ServiceType.IOT_FLEETWISE,
    },
    "media": {
        ServiceType.MEDIA_CONNECT,
        ServiceType.MEDIA_CONVERT,
        ServiceType.MEDIA_LIVE,
        ServiceType.MEDIA_PACKAGE,
        ServiceType.MEDIA_STORE,
        ServiceType.MEDIA_TAILOR,
        ServiceType.INTERACTIVE_VIDEO_SERVICE,
        ServiceType.KINESIS_VIDEO_STREAMS,
    },
    "machine-learning": {
        ServiceType.BEDROCK,
        ServiceType.SAGEMAKER,
        ServiceType.AMAZON_Q,
        ServiceType.BEDROCK_AGENT,
        ServiceType.BEDROCK_GUARDRAIL,
        ServiceType.BEDROCK_KNOWLEDGE_BASE,
        ServiceType.BEDROCK_AGENTCORE,
        ServiceType.COMPREHEND,
        ServiceType.COMPREHEND_MEDICAL,
        ServiceType.TEXTRACT,
        ServiceType.REKOGNITION,
        ServiceType.TRANSCRIBE,
        ServiceType.TRANSLATE,
        ServiceType.PERSONALIZE,
        ServiceType.KENDRA,
        ServiceType.LEX,
        ServiceType.FORECAST,
        ServiceType.FRAUD_DETECTOR,
        ServiceType.HEALTHLAKE,
    },
    "management-governance": {
        ServiceType.CLOUDWATCH,
        ServiceType.CLOUDTRAIL,
        ServiceType.AWS_CONFIG,
        ServiceType.SYSTEMS_MANAGER,
        ServiceType.ORGANIZATIONS,
        ServiceType.CONTROL_TOWER,
        ServiceType.MANAGED_GRAFANA,
        ServiceType.MANAGED_PROMETHEUS,
        ServiceType.FAULT_INJECTION_SIMULATOR,
    },
    "security": {
        ServiceType.IAM,
        ServiceType.KMS,
        ServiceType.SECRETS_MANAGER,
        ServiceType.COGNITO,
        ServiceType.CERTIFICATE_MANAGER,
        ServiceType.WAF,
        ServiceType.NETWORK_FIREWALL,
        ServiceType.GUARDDUTY,
        ServiceType.SECURITY_HUB,
        ServiceType.MACIE,
        ServiceType.INSPECTOR,
        ServiceType.FIREWALL_MANAGER,
        ServiceType.PRIVATE_CERTIFICATE_AUTHORITY,
        ServiceType.VERIFIED_PERMISSIONS,
    },
    "storage": {ServiceType.S3, ServiceType.EBS, ServiceType.EFS, ServiceType.BACKUP},
    "app-integration": {
        ServiceType.API_GATEWAY,
        ServiceType.EVENTBRIDGE,
        ServiceType.SNS,
        ServiceType.SQS,
        ServiceType.STEP_FUNCTIONS,
        ServiceType.APPSYNC,
        ServiceType.MQ,
        ServiceType.MWAA,
    },
    "migration-transfer": {
        ServiceType.DATASYNC,
        ServiceType.TRANSFER_FAMILY,
        ServiceType.APPLICATION_MIGRATION_SERVICE,
        ServiceType.MAINFRAME_MODERNIZATION,
        ServiceType.MIGRATION_HUB,
    },
    "networking": {
        ServiceType.VPC,
        ServiceType.SUBNET,
        ServiceType.SECURITY_GROUP,
        ServiceType.ROUTE_TABLE,
        ServiceType.INTERNET_GATEWAY,
        ServiceType.NAT_GATEWAY,
        ServiceType.LOAD_BALANCER,
        ServiceType.TARGET_GROUP,
        ServiceType.ROUTE53,
        ServiceType.CLOUDFRONT,
        ServiceType.TRANSIT_GATEWAY,
        ServiceType.DIRECT_CONNECT,
        ServiceType.VPC_LATTICE,
        ServiceType.GLOBAL_ACCELERATOR,
        ServiceType.SITE_TO_SITE_VPN,
        ServiceType.CLIENT_VPN,
    },
}

_CAPABILITIES = {
    ServiceType.COMPREHEND_MEDICAL,
    ServiceType.TEXTRACT,
    ServiceType.TRANSLATE,
    ServiceType.PERSONALIZE,
    ServiceType.FORECAST,
    ServiceType.FRAUD_DETECTOR,
    ServiceType.HEALTHLAKE,
    ServiceType.IOT_GREENGRASS,
    ServiceType.IOT_DEVICE_DEFENDER,
    ServiceType.IOT_EVENTS,
    ServiceType.IOT_SITEWISE,
    ServiceType.IOT_TWINMAKER,
    ServiceType.IOT_FLEETWISE,
    ServiceType.MEDIA_CONNECT,
    ServiceType.MEDIA_CONVERT,
    ServiceType.MEDIA_PACKAGE,
    ServiceType.MEDIA_TAILOR,
    ServiceType.KINESIS_VIDEO_STREAMS,
    ServiceType.APPLICATION_MIGRATION_SERVICE,
    ServiceType.MAINFRAME_MODERNIZATION,
    ServiceType.MIGRATION_HUB,
    ServiceType.BOTTLEROCKET,
    ServiceType.ELASTIC_FABRIC_ADAPTER,
    ServiceType.FARGATE,
    ServiceType.LOCAL_ZONES,
    ServiceType.NITRO_ENCLAVES,
    ServiceType.OUTPOSTS_FAMILY,
    ServiceType.WAVELENGTH,
    ServiceType.ECS_ANYWHERE,
    ServiceType.EKS_ANYWHERE,
    ServiceType.EKS_CLOUD,
    ServiceType.EKS_DISTRO,
    ServiceType.PINPOINT_APIS,
    ServiceType.APPLICATION_COMPOSER,
    ServiceType.CLOUD_CONTROL_API,
    ServiceType.CLOUD_DEVELOPMENT_KIT,
    ServiceType.COMMAND_LINE_INTERFACE,
    ServiceType.CORRETTO,
    ServiceType.TOOLS_AND_SDKS,
}
_COMPOSITES = {
    ServiceType.OUTPOSTS_RACK,
    ServiceType.CONTROL_TOWER,
    ServiceType.OUTPOSTS_SERVERS,
    ServiceType.WORKSPACES_FAMILY,
    ServiceType.VMWARE_CLOUD_ON_AWS,
    ServiceType.RED_HAT_OPENSHIFT,
}
_DECORATIVE = {
    ServiceType.ACTIVATE,
    ServiceType.IQ,
    ServiceType.MANAGED_SERVICES,
    ServiceType.PROFESSIONAL_SERVICES,
    ServiceType.REPOST,
    ServiceType.SUPPORT,
    ServiceType.TRAINING_CERTIFICATION,
    ServiceType.CLOUDSHELL,
}
_RETIRED = {
    ServiceType.ALEXA_FOR_BUSINESS,
    ServiceType.DATA_PIPELINE,
    ServiceType.GLUE_ELASTIC_VIEWS,
    ServiceType.KINESIS_DATA_ANALYTICS,
    ServiceType.HONEYCODE,
    ServiceType.WORKLINK,
    ServiceType.GAMEKIT,
    ServiceType.GAMESPARKS,
    ServiceType.LUMBERYARD,
    ServiceType.OPEN_3D_ENGINE,
    ServiceType.THINKBOX_FROST,
    ServiceType.THINKBOX_KRAKATOA,
    ServiceType.THINKBOX_SEQUOIA,
    ServiceType.THINKBOX_STOKE,
    ServiceType.THINKBOX_XMESH,
    ServiceType.MEDIA_STORE,
}
_DEPRECATED = {
    ServiceType.CLOUD9,
    ServiceType.RDS_ON_VMWARE,
    ServiceType.IOT_ANALYTICS,
}


def _category_for(service_type: ServiceType) -> str:
    matches = [
        name for name, members in _CATEGORY_MEMBERS.items() if service_type in members
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Service {service_type.value} has {len(matches)} catalog categories"
        )
    return matches[0]


def _classification_for(service_type: ServiceType) -> ServiceClassification:
    if service_type in _RETIRED or service_type in _DEPRECATED:
        return ServiceClassification.LEGACY
    if service_type in _DECORATIVE:
        return ServiceClassification.DECORATIVE
    if service_type in _COMPOSITES:
        return ServiceClassification.COMPOSITE
    if service_type in _CAPABILITIES:
        return ServiceClassification.CAPABILITY
    return ServiceClassification.RESOURCE


def _lifecycle_for(service_type: ServiceType) -> ServiceLifecycle:
    if service_type in _RETIRED:
        return ServiceLifecycle.RETIRED
    if service_type in _DEPRECATED:
        return ServiceLifecycle.DEPRECATED
    if service_type in _DECORATIVE:
        return ServiceLifecycle.DECORATIVE
    return ServiceLifecycle.ACTIVE


def build_service_catalog() -> dict[ServiceType, ServiceMetadata]:
    config_models = get_service_config_models()
    connected = {spec.source for spec in CONNECTION_SPECS} | {
        spec.target for spec in CONNECTION_SPECS
    }
    catalog = {}
    for service_type in ServiceType:
        terraform = service_type in GENERATOR_REGISTRY
        lifecycle = _lifecycle_for(service_type)
        catalog[service_type] = ServiceMetadata(
            display_name=service_type.value.replace("-", " ").title(),
            category=_category_for(service_type),
            classification=_classification_for(service_type),
            lifecycle=lifecycle,
            capabilities=ServiceCapabilitiesResponse(
                diagram=lifecycle
                not in {ServiceLifecycle.RETIRED, ServiceLifecycle.DECORATIVE},
                terraform=terraform,
                configurable=service_type in config_models and terraform,
                connectable=service_type in connected,
            ),
        )
    return catalog


SERVICE_CATALOG = build_service_catalog()
