"""Input models package — re-exports all public types for backward compatibility."""

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._connections import ConnectionInput
from app.models.input_models._general import (
    ArchitectureDescription,
    Connection,
    EnvironmentConfig,
    GlobalTerraformConfig,
    ResourceConfig,
    ResourceInstance,
    ServiceType,
    get_service_config_models,
)
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    TerraformMeta,
    ValidationRule,
    VariableSchemaEntry,
    VisibleWhen,
    get_terraform_meta,
)

# Per-service config models
from app.models.input_models.amazon_q_config import AmazonQConfig
from app.models.input_models.amplify_config import AmplifyConfig
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.input_models.app_runner_config import AppRunnerConfig
from app.models.input_models.appstream_config import AppStreamConfig
from app.models.input_models.athena_config import AthenaConfig
from app.models.input_models.aurora_config import AuroraConfig
from app.models.input_models.batch_config import BatchConfig
from app.models.input_models.bedrock_agent_config import BedrockAgentConfig
from app.models.input_models.bedrock_agentcore_config import BedrockAgentcoreConfig
from app.models.input_models.bedrock_config import BedrockConfig
from app.models.input_models.bedrock_guardrail_config import BedrockGuardrailConfig
from app.models.input_models.bedrock_knowledge_base_config import (
    BedrockKnowledgeBaseConfig,
)
from app.models.input_models.cloudsearch_config import CloudSearchConfig
from app.models.input_models.cloudwatch_config import CloudWatchConfig
from app.models.input_models.codebuild_config import CodeBuildConfig
from app.models.input_models.codecommit_config import CodeCommitConfig
from app.models.input_models.codedeploy_config import CodeDeployConfig
from app.models.input_models.codepipeline_config import CodePipelineConfig
from app.models.input_models.connect_config import ConnectConfig
from app.models.input_models.documentdb_config import DocumentDbConfig
from app.models.input_models.dynamodb_config import DynamoDBConfig
from app.models.input_models.ec2_config import Ec2Config
from app.models.input_models.ec2_image_builder_config import Ec2ImageBuilderConfig
from app.models.input_models.ecr_config import EcrConfig
from app.models.input_models.ecs_config import EcsConfig
from app.models.input_models.eks_config import EksConfig
from app.models.input_models.elastic_beanstalk_config import ElasticBeanstalkConfig
from app.models.input_models.elasticache_config import ElastiCacheConfig
from app.models.input_models.emr_config import EmrConfig
from app.models.input_models.gamelift_config import GameLiftConfig
from app.models.input_models.glue_config import GlueConfig
from app.models.input_models.kinesis_config import KinesisConfig
from app.models.input_models.kinesis_firehose_config import KinesisFirehoseConfig
from app.models.input_models.lambda_config import LambdaConfig
from app.models.input_models.lightsail_config import LightsailConfig
from app.models.input_models.msk_config import MskConfig
from app.models.input_models.neptune_config import NeptuneConfig
from app.models.input_models.opensearch_config import OpenSearchConfig
from app.models.input_models.pinpoint_config import PinpointConfig
from app.models.input_models.rds_config import RdsConfig
from app.models.input_models.redshift_config import RedshiftConfig
from app.models.input_models.s3_config import S3Config
from app.models.input_models.sagemaker_config import SageMakerConfig
from app.models.input_models.ses_config import SesConfig
from app.models.input_models.sns_config import SnsConfig
from app.models.input_models.sqs_config import SqsConfig
from app.models.input_models.timestream_config import TimestreamConfig

# Build registry after all config models are imported (avoids circular import)
SERVICE_CONFIG_MODELS: dict = {
    ServiceType.LAMBDA: LambdaConfig,
    ServiceType.S3: S3Config,
    ServiceType.API_GATEWAY: ApiGatewayConfig,
    ServiceType.DYNAMODB: DynamoDBConfig,
    ServiceType.CLOUDWATCH: CloudWatchConfig,
    ServiceType.SNS: SnsConfig,
    ServiceType.SQS: SqsConfig,
    ServiceType.EC2: Ec2Config,
    ServiceType.ECS: EcsConfig,
    ServiceType.EKS: EksConfig,
    ServiceType.ELASTIC_BEANSTALK: ElasticBeanstalkConfig,
    ServiceType.APP_RUNNER: AppRunnerConfig,
    ServiceType.BATCH: BatchConfig,
    ServiceType.EC2_IMAGE_BUILDER: Ec2ImageBuilderConfig,
    ServiceType.LIGHTSAIL: LightsailConfig,
    ServiceType.ECR: EcrConfig,
    ServiceType.ATHENA: AthenaConfig,
    ServiceType.CLOUDSEARCH: CloudSearchConfig,
    ServiceType.EMR: EmrConfig,
    ServiceType.GLUE: GlueConfig,
    ServiceType.KINESIS: KinesisConfig,
    ServiceType.KINESIS_FIREHOSE: KinesisFirehoseConfig,
    ServiceType.MSK: MskConfig,
    ServiceType.OPENSEARCH: OpenSearchConfig,
    ServiceType.REDSHIFT: RedshiftConfig,
    ServiceType.CONNECT: ConnectConfig,
    ServiceType.SES: SesConfig,
    ServiceType.PINPOINT: PinpointConfig,
    ServiceType.AURORA: AuroraConfig,
    ServiceType.DOCUMENTDB: DocumentDbConfig,
    ServiceType.ELASTICACHE: ElastiCacheConfig,
    ServiceType.NEPTUNE: NeptuneConfig,
    ServiceType.RDS: RdsConfig,
    ServiceType.TIMESTREAM: TimestreamConfig,
    ServiceType.CODEBUILD: CodeBuildConfig,
    ServiceType.CODECOMMIT: CodeCommitConfig,
    ServiceType.CODEDEPLOY: CodeDeployConfig,
    ServiceType.CODEPIPELINE: CodePipelineConfig,
    ServiceType.APPSTREAM: AppStreamConfig,
    ServiceType.AMPLIFY: AmplifyConfig,
    ServiceType.GAMELIFT: GameLiftConfig,
    ServiceType.BEDROCK: BedrockConfig,
    ServiceType.SAGEMAKER: SageMakerConfig,
    ServiceType.AMAZON_Q: AmazonQConfig,
    ServiceType.BEDROCK_AGENT: BedrockAgentConfig,
    ServiceType.BEDROCK_GUARDRAIL: BedrockGuardrailConfig,
    ServiceType.BEDROCK_KNOWLEDGE_BASE: BedrockKnowledgeBaseConfig,
    ServiceType.BEDROCK_AGENTCORE: BedrockAgentcoreConfig,
}

__all__ = [
    # General definitions
    "ArchitectureDescription",
    "BaseServiceConfig",
    "Connection",
    "EnvironmentConfig",
    "GlobalTerraformConfig",
    "ResourceConfig",
    "ResourceInstance",
    "ServiceType",
    # Terraform field metadata
    "ConnectionInput",
    "OptionEntry",
    "TerraformField",
    "TerraformMeta",
    "ValidationRule",
    "VariableSchemaEntry",
    "VisibleWhen",
    "get_terraform_meta",
    # Registry
    "SERVICE_CONFIG_MODELS",
    "get_service_config_models",
    # Per-service config models
    "AmazonQConfig",
    "AmplifyConfig",
    "ApiGatewayConfig",
    "AppRunnerConfig",
    "AppStreamConfig",
    "AthenaConfig",
    "AuroraConfig",
    "BatchConfig",
    "BedrockAgentConfig",
    "BedrockAgentcoreConfig",
    "BedrockConfig",
    "BedrockGuardrailConfig",
    "BedrockKnowledgeBaseConfig",
    "CloudSearchConfig",
    "CloudWatchConfig",
    "CodeBuildConfig",
    "CodeCommitConfig",
    "CodeDeployConfig",
    "CodePipelineConfig",
    "ConnectConfig",
    "DocumentDbConfig",
    "DynamoDBConfig",
    "Ec2Config",
    "Ec2ImageBuilderConfig",
    "EcrConfig",
    "EcsConfig",
    "EksConfig",
    "ElasticBeanstalkConfig",
    "ElastiCacheConfig",
    "EmrConfig",
    "GameLiftConfig",
    "GlueConfig",
    "KinesisConfig",
    "KinesisFirehoseConfig",
    "LambdaConfig",
    "LightsailConfig",
    "MskConfig",
    "NeptuneConfig",
    "OpenSearchConfig",
    "PinpointConfig",
    "RdsConfig",
    "RedshiftConfig",
    "S3Config",
    "SageMakerConfig",
    "SesConfig",
    "SnsConfig",
    "SqsConfig",
    "TimestreamConfig",
]
