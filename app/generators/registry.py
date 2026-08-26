"""Service generator registry — maps ServiceType to generator instances."""

from app.generators.acm_generator import AcmGenerator
from app.generators.amazon_q_generator import AmazonQGenerator

# Front End Web Mobile generators
from app.generators.amplify_generator import AmplifyGenerator
from app.generators.api_gateway_generator import APIGatewayGenerator
from app.generators.app_runner_generator import AppRunnerGenerator
from app.generators.application_auto_scaling_generator import (
    ApplicationAutoScalingGenerator,
)

# End User Computing generators
from app.generators.appstream_generator import AppStreamGenerator
from app.generators.appsync_generator import AppSyncGenerator

# Analytics generators
from app.generators.athena_generator import AthenaGenerator

# Database generators
from app.generators.aurora_generator import AuroraGenerator
from app.generators.backup_generator import BackupGenerator
from app.generators.base import ServiceGenerator
from app.generators.batch_generator import BatchGenerator
from app.generators.bedrock_agent_generator import BedrockAgentGenerator
from app.generators.bedrock_agentcore_generator import BedrockAgentCoreGenerator

# Machine Learning generators
from app.generators.bedrock_generator import BedrockGenerator
from app.generators.bedrock_guardrail_generator import BedrockGuardrailGenerator
from app.generators.bedrock_knowledge_base_generator import (
    BedrockKnowledgeBaseGenerator,
)
from app.generators.cloudfront_generator import CloudFrontGenerator
from app.generators.cloudsearch_generator import CloudSearchGenerator
from app.generators.cloudwatch_generator import CloudWatchGenerator

# Developer Tools generators
from app.generators.codebuild_generator import CodeBuildGenerator
from app.generators.codecommit_generator import CodeCommitGenerator
from app.generators.codedeploy_generator import CodeDeployGenerator
from app.generators.codepipeline_generator import CodePipelineGenerator
from app.generators.cognito_generator import CognitoGenerator

# Business Applications generators
from app.generators.connect_generator import ConnectGenerator
from app.generators.dms_generator import DmsGenerator
from app.generators.documentdb_generator import DocumentDBGenerator
from app.generators.dynamodb_generator import DynamoDBGenerator
from app.generators.ebs_generator import EbsGenerator
from app.generators.ec2_auto_scaling_generator import Ec2AutoScalingGenerator
from app.generators.ec2_generator import EC2Generator
from app.generators.ec2_image_builder_generator import EC2ImageBuilderGenerator
from app.generators.ecr_generator import ECRGenerator
from app.generators.ecs_generator import ECSGenerator
from app.generators.efs_generator import EfsGenerator
from app.generators.eks_generator import EKSGenerator
from app.generators.elastic_beanstalk_generator import ElasticBeanstalkGenerator
from app.generators.elasticache_generator import ElastiCacheGenerator
from app.generators.emr_generator import EMRGenerator
from app.generators.eventbridge_generator import EventBridgeGenerator

# Games generators
from app.generators.gamelift_generator import GameLiftGenerator
from app.generators.glue_generator import GlueGenerator
from app.generators.iam_generator import IAMGenerator
from app.generators.internet_gateway_generator import InternetGatewayGenerator
from app.generators.keyspaces_generator import KeyspacesGenerator
from app.generators.kinesis_firehose_generator import KinesisFirehoseGenerator
from app.generators.kinesis_generator import KinesisGenerator
from app.generators.kms_generator import KmsGenerator
from app.generators.lambda_generator import LambdaGenerator
from app.generators.lightsail_generator import LightsailGenerator
from app.generators.load_balancer_generator import LoadBalancerGenerator
from app.generators.memorydb_generator import MemoryDbGenerator
from app.generators.mq_generator import MqGenerator
from app.generators.msk_generator import MSKGenerator
from app.generators.mwaa_generator import MwaaGenerator
from app.generators.nat_gateway_generator import NatGatewayGenerator
from app.generators.neptune_generator import NeptuneGenerator
from app.generators.opensearch_generator import OpenSearchGenerator
from app.generators.pinpoint_generator import PinpointGenerator
from app.generators.rds_generator import RDSGenerator
from app.generators.redshift_generator import RedshiftGenerator
from app.generators.route53_generator import Route53Generator
from app.generators.route_table_generator import RouteTableGenerator
from app.generators.s3_generator import S3Generator
from app.generators.sagemaker_generator import SageMakerGenerator
from app.generators.secrets_manager_generator import SecretsManagerGenerator
from app.generators.security_group_generator import SecurityGroupGenerator
from app.generators.ses_generator import SESGenerator
from app.generators.sns_generator import SNSGenerator
from app.generators.sqs_generator import SQSGenerator
from app.generators.step_functions_generator import StepFunctionsGenerator
from app.generators.subnet_generator import SubnetGenerator
from app.generators.target_group_generator import TargetGroupGenerator
from app.generators.timestream_generator import TimestreamGenerator
from app.generators.vpc_generator import VpcGenerator
from app.generators.waf_generator import WafGenerator
from app.models.input_models import ServiceType

GENERATOR_REGISTRY: dict[ServiceType, ServiceGenerator] = {
    ServiceType.LAMBDA: LambdaGenerator(),
    ServiceType.S3: S3Generator(),
    ServiceType.DYNAMODB: DynamoDBGenerator(),
    ServiceType.API_GATEWAY: APIGatewayGenerator(),
    ServiceType.CLOUDWATCH: CloudWatchGenerator(),
    ServiceType.IAM: IAMGenerator(),
    ServiceType.EVENTBRIDGE: EventBridgeGenerator(),
    ServiceType.SNS: SNSGenerator(),
    ServiceType.SQS: SQSGenerator(),
    ServiceType.VPC: VpcGenerator(),
    ServiceType.SUBNET: SubnetGenerator(),
    ServiceType.SECURITY_GROUP: SecurityGroupGenerator(),
    ServiceType.ROUTE_TABLE: RouteTableGenerator(),
    ServiceType.INTERNET_GATEWAY: InternetGatewayGenerator(),
    ServiceType.NAT_GATEWAY: NatGatewayGenerator(),
    ServiceType.LOAD_BALANCER: LoadBalancerGenerator(),
    ServiceType.TARGET_GROUP: TargetGroupGenerator(),
    ServiceType.ROUTE53: Route53Generator(),
    ServiceType.CLOUDFRONT: CloudFrontGenerator(),
    ServiceType.KMS: KmsGenerator(),
    ServiceType.SECRETS_MANAGER: SecretsManagerGenerator(),
    ServiceType.COGNITO: CognitoGenerator(),
    ServiceType.CERTIFICATE_MANAGER: AcmGenerator(),
    ServiceType.WAF: WafGenerator(),
    ServiceType.EBS: EbsGenerator(),
    ServiceType.EFS: EfsGenerator(),
    ServiceType.BACKUP: BackupGenerator(),
    ServiceType.STEP_FUNCTIONS: StepFunctionsGenerator(),
    ServiceType.APPSYNC: AppSyncGenerator(),
    ServiceType.MQ: MqGenerator(),
    ServiceType.MWAA: MwaaGenerator(),
    ServiceType.EC2_AUTO_SCALING: Ec2AutoScalingGenerator(),
    ServiceType.APPLICATION_AUTO_SCALING: ApplicationAutoScalingGenerator(),
    ServiceType.EC2: EC2Generator(),
    ServiceType.ECS: ECSGenerator(),
    ServiceType.EKS: EKSGenerator(),
    ServiceType.ELASTIC_BEANSTALK: ElasticBeanstalkGenerator(),
    ServiceType.APP_RUNNER: AppRunnerGenerator(),
    ServiceType.BATCH: BatchGenerator(),
    ServiceType.EC2_IMAGE_BUILDER: EC2ImageBuilderGenerator(),
    ServiceType.LIGHTSAIL: LightsailGenerator(),
    ServiceType.ECR: ECRGenerator(),
    # Analytics
    ServiceType.ATHENA: AthenaGenerator(),
    ServiceType.CLOUDSEARCH: CloudSearchGenerator(),
    ServiceType.EMR: EMRGenerator(),
    ServiceType.GLUE: GlueGenerator(),
    ServiceType.KINESIS: KinesisGenerator(),
    ServiceType.KINESIS_FIREHOSE: KinesisFirehoseGenerator(),
    ServiceType.MSK: MSKGenerator(),
    ServiceType.OPENSEARCH: OpenSearchGenerator(),
    ServiceType.REDSHIFT: RedshiftGenerator(),
    # Business Applications
    ServiceType.CONNECT: ConnectGenerator(),
    ServiceType.SES: SESGenerator(),
    ServiceType.PINPOINT: PinpointGenerator(),
    # Database
    ServiceType.AURORA: AuroraGenerator(),
    ServiceType.DOCUMENTDB: DocumentDBGenerator(),
    ServiceType.ELASTICACHE: ElastiCacheGenerator(),
    ServiceType.NEPTUNE: NeptuneGenerator(),
    ServiceType.RDS: RDSGenerator(),
    ServiceType.TIMESTREAM: TimestreamGenerator(),
    ServiceType.DATABASE_MIGRATION_SERVICE: DmsGenerator(),
    ServiceType.KEYSPACES: KeyspacesGenerator(),
    ServiceType.MEMORYDB: MemoryDbGenerator(),
    # Developer Tools
    ServiceType.CODEBUILD: CodeBuildGenerator(),
    ServiceType.CODECOMMIT: CodeCommitGenerator(),
    ServiceType.CODEDEPLOY: CodeDeployGenerator(),
    ServiceType.CODEPIPELINE: CodePipelineGenerator(),
    # End User Computing
    ServiceType.APPSTREAM: AppStreamGenerator(),
    # Front End Web Mobile
    ServiceType.AMPLIFY: AmplifyGenerator(),
    # Games
    ServiceType.GAMELIFT: GameLiftGenerator(),
    # Machine Learning
    ServiceType.BEDROCK: BedrockGenerator(),
    ServiceType.SAGEMAKER: SageMakerGenerator(),
    ServiceType.AMAZON_Q: AmazonQGenerator(),
    ServiceType.BEDROCK_AGENT: BedrockAgentGenerator(),
    ServiceType.BEDROCK_GUARDRAIL: BedrockGuardrailGenerator(),
    ServiceType.BEDROCK_KNOWLEDGE_BASE: BedrockKnowledgeBaseGenerator(),
    ServiceType.BEDROCK_AGENTCORE: BedrockAgentCoreGenerator(),
}
