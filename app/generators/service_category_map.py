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
    # Application integration
    ServiceType.STEP_FUNCTIONS: "app-integration",
    ServiceType.APPSYNC: "app-integration",
    ServiceType.MQ: "app-integration",
    ServiceType.MWAA: "app-integration",
    # Log/Monitoring
    ServiceType.CLOUDWATCH: "log",
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
    # Machine Learning
    ServiceType.BEDROCK: "machine-learning",
    ServiceType.SAGEMAKER: "machine-learning",
    ServiceType.AMAZON_Q: "machine-learning",
    ServiceType.BEDROCK_AGENT: "machine-learning",
    ServiceType.BEDROCK_GUARDRAIL: "machine-learning",
    ServiceType.BEDROCK_KNOWLEDGE_BASE: "machine-learning",
    ServiceType.BEDROCK_AGENTCORE: "machine-learning",
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
