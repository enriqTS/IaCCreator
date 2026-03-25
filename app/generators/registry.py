"""Service generator registry — maps ServiceType to generator instances."""

from app.models.input_models import ServiceType
from app.generators.base import ServiceGenerator
from app.generators.lambda_generator import LambdaGenerator
from app.generators.s3_generator import S3Generator
from app.generators.dynamodb_generator import DynamoDBGenerator
from app.generators.api_gateway_generator import APIGatewayGenerator
from app.generators.cloudwatch_generator import CloudWatchGenerator
from app.generators.iam_generator import IAMGenerator

GENERATOR_REGISTRY: dict[ServiceType, ServiceGenerator] = {
    ServiceType.LAMBDA: LambdaGenerator(),
    ServiceType.S3: S3Generator(),
    ServiceType.DYNAMODB: DynamoDBGenerator(),
    ServiceType.API_GATEWAY: APIGatewayGenerator(),
    ServiceType.CLOUDWATCH: CloudWatchGenerator(),
    ServiceType.IAM: IAMGenerator(),
}
