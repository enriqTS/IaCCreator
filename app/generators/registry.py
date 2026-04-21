"""Service generator registry — maps ServiceType to generator instances."""

from app.models.input_models import ServiceType
from app.generators.base import ServiceGenerator
from app.generators.lambda_generator import LambdaGenerator
from app.generators.s3_generator import S3Generator
from app.generators.dynamodb_generator import DynamoDBGenerator
from app.generators.api_gateway_generator import APIGatewayGenerator
from app.generators.cloudwatch_generator import CloudWatchGenerator
from app.generators.iam_generator import IAMGenerator
from app.generators.sns_generator import SNSGenerator
from app.generators.sqs_generator import SQSGenerator
from app.generators.ec2_generator import EC2Generator
from app.generators.ecs_generator import ECSGenerator
from app.generators.eks_generator import EKSGenerator
from app.generators.elastic_beanstalk_generator import ElasticBeanstalkGenerator
from app.generators.app_runner_generator import AppRunnerGenerator
from app.generators.batch_generator import BatchGenerator
from app.generators.ec2_image_builder_generator import EC2ImageBuilderGenerator
from app.generators.lightsail_generator import LightsailGenerator
from app.generators.ecr_generator import ECRGenerator

GENERATOR_REGISTRY: dict[ServiceType, ServiceGenerator] = {
    ServiceType.LAMBDA: LambdaGenerator(),
    ServiceType.S3: S3Generator(),
    ServiceType.DYNAMODB: DynamoDBGenerator(),
    ServiceType.API_GATEWAY: APIGatewayGenerator(),
    ServiceType.CLOUDWATCH: CloudWatchGenerator(),
    ServiceType.IAM: IAMGenerator(),
    ServiceType.SNS: SNSGenerator(),
    ServiceType.SQS: SQSGenerator(),
    ServiceType.EC2: EC2Generator(),
    ServiceType.ECS: ECSGenerator(),
    ServiceType.EKS: EKSGenerator(),
    ServiceType.ELASTIC_BEANSTALK: ElasticBeanstalkGenerator(),
    ServiceType.APP_RUNNER: AppRunnerGenerator(),
    ServiceType.BATCH: BatchGenerator(),
    ServiceType.EC2_IMAGE_BUILDER: EC2ImageBuilderGenerator(),
    ServiceType.LIGHTSAIL: LightsailGenerator(),
    ServiceType.ECR: ECRGenerator(),
}
