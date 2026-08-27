"""Centralized service-to-category mapping."""

from app.models.input_models import ServiceType

SERVICE_CATEGORY_MAP: dict[ServiceType, str] = {
    # Compute
    ServiceType.LAMBDA: "compute",
    ServiceType.EC2: "compute",
    ServiceType.ECS: "compute",
    ServiceType.EKS: "compute",
    ServiceType.ELASTIC_BEANSTALK: "compute",
    ServiceType.APP_RUNNER: "compute",
    ServiceType.BATCH: "compute",
    ServiceType.EC2_IMAGE_BUILDER: "compute",
    ServiceType.LIGHTSAIL: "compute",
    ServiceType.ECR: "compute",
    ServiceType.EC2_AUTO_SCALING: "compute",
    ServiceType.APPLICATION_AUTO_SCALING: "compute",
    # Database
    ServiceType.DYNAMODB: "database",
    ServiceType.AURORA: "database",
    ServiceType.DOCUMENTDB: "database",
    ServiceType.ELASTICACHE: "database",
    ServiceType.NEPTUNE: "database",
    ServiceType.RDS: "database",
    ServiceType.TIMESTREAM: "database",
    ServiceType.DATABASE_MIGRATION_SERVICE: "database",
    ServiceType.KEYSPACES: "database",
    ServiceType.MEMORYDB: "database",
    # Storage
    ServiceType.S3: "storage",
    ServiceType.EBS: "storage",
    ServiceType.EFS: "storage",
    ServiceType.BACKUP: "storage",
    # Networking
    ServiceType.API_GATEWAY: "networking",
    ServiceType.VPC: "networking",
    ServiceType.SUBNET: "networking",
    ServiceType.SECURITY_GROUP: "networking",
    ServiceType.ROUTE_TABLE: "networking",
    ServiceType.INTERNET_GATEWAY: "networking",
    ServiceType.NAT_GATEWAY: "networking",
    ServiceType.LOAD_BALANCER: "networking",
    ServiceType.TARGET_GROUP: "networking",
    ServiceType.ROUTE53: "networking",
    ServiceType.CLOUDFRONT: "networking",
    ServiceType.TRANSIT_GATEWAY: "networking",
    ServiceType.DIRECT_CONNECT: "networking",
    ServiceType.VPC_LATTICE: "networking",
    ServiceType.GLOBAL_ACCELERATOR: "networking",
    ServiceType.SITE_TO_SITE_VPN: "networking",
    ServiceType.CLIENT_VPN: "networking",
    # Application integration
    ServiceType.STEP_FUNCTIONS: "app-integration",
    ServiceType.APPSYNC: "app-integration",
    ServiceType.MQ: "app-integration",
    ServiceType.MWAA: "app-integration",
    # Management and governance
    ServiceType.CLOUDWATCH: "log",
    ServiceType.CLOUDTRAIL: "management-governance",
    ServiceType.AWS_CONFIG: "management-governance",
    ServiceType.SYSTEMS_MANAGER: "management-governance",
    ServiceType.ORGANIZATIONS: "management-governance",
    ServiceType.MANAGED_GRAFANA: "management-governance",
    ServiceType.MANAGED_PROMETHEUS: "management-governance",
    ServiceType.FAULT_INJECTION_SIMULATOR: "management-governance",
    # Messaging
    ServiceType.SNS: "messaging",
    ServiceType.SQS: "messaging",
    ServiceType.EVENTBRIDGE: "messaging",
    # Analytics
    ServiceType.ATHENA: "analytics",
    ServiceType.CLOUDSEARCH: "analytics",
    ServiceType.EMR: "analytics",
    ServiceType.GLUE: "analytics",
    ServiceType.KINESIS: "analytics",
    ServiceType.KINESIS_FIREHOSE: "analytics",
    ServiceType.MSK: "analytics",
    ServiceType.OPENSEARCH: "analytics",
    ServiceType.REDSHIFT: "analytics",
    ServiceType.QUICKSIGHT: "analytics",
    ServiceType.LAKE_FORMATION: "analytics",
    ServiceType.DATAZONE: "analytics",
    # Developer Tools
    ServiceType.CODEARTIFACT: "developer-tools",
    ServiceType.X_RAY: "developer-tools",
    ServiceType.CODEBUILD: "developer-tools",
    ServiceType.CODECOMMIT: "developer-tools",
    ServiceType.CODEDEPLOY: "developer-tools",
    ServiceType.CODEPIPELINE: "developer-tools",
    # Business Applications
    ServiceType.CONNECT: "business-applications",
    ServiceType.SES: "business-applications",
    ServiceType.PINPOINT: "business-applications",
    # Security
    ServiceType.IAM: "security",
    ServiceType.KMS: "security",
    ServiceType.SECRETS_MANAGER: "security",
    ServiceType.COGNITO: "security",
    ServiceType.CERTIFICATE_MANAGER: "security",
    ServiceType.WAF: "security",
    ServiceType.NETWORK_FIREWALL: "security",
    ServiceType.GUARDDUTY: "security",
    ServiceType.SECURITY_HUB: "security",
    ServiceType.MACIE: "security",
    ServiceType.INSPECTOR: "security",
    ServiceType.FIREWALL_MANAGER: "security",
    ServiceType.PRIVATE_CERTIFICATE_AUTHORITY: "security",
    ServiceType.VERIFIED_PERMISSIONS: "security",
    # Machine Learning
    ServiceType.BEDROCK: "machine-learning",
    ServiceType.SAGEMAKER: "machine-learning",
    ServiceType.AMAZON_Q: "machine-learning",
    ServiceType.BEDROCK_AGENT: "machine-learning",
    ServiceType.BEDROCK_GUARDRAIL: "machine-learning",
    ServiceType.BEDROCK_KNOWLEDGE_BASE: "machine-learning",
    ServiceType.BEDROCK_AGENTCORE: "machine-learning",
    ServiceType.COMPREHEND: "machine-learning",
    ServiceType.REKOGNITION: "machine-learning",
    ServiceType.TRANSCRIBE: "machine-learning",
    ServiceType.KENDRA: "machine-learning",
    ServiceType.LEX: "machine-learning",
    # Internet of Things
    ServiceType.IOT_CORE: "internet-of-things",
    ServiceType.IOT_DEVICE_MANAGEMENT: "internet-of-things",
    # Media
    ServiceType.MEDIA_LIVE: "media",
    ServiceType.INTERACTIVE_VIDEO_SERVICE: "media",
    # Migration and transfer
    ServiceType.DATASYNC: "migration-transfer",
    ServiceType.TRANSFER_FAMILY: "migration-transfer",
    # End user computing
    ServiceType.WORKSPACES: "end-user-computing",
    # Other
    ServiceType.APPSTREAM: "other",
    ServiceType.AMPLIFY: "other",
    ServiceType.GAMELIFT: "other",
}

_DEFAULT_CATEGORY = "other"


def get_category(service_type: ServiceType) -> str:
    """Return the category folder name for a given service type.

    Falls back to "other" when the service type has no explicit mapping.
    """
    return SERVICE_CATEGORY_MAP.get(service_type, _DEFAULT_CATEGORY)
