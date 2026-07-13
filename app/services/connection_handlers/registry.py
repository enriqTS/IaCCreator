"""Connection handler registry — maps (source_service, target_service) to handler instances."""

from app.models.input_models import ServiceType
from app.services.connection_handlers.apigw_lambda import ApiGatewayLambdaHandler
from app.services.connection_handlers.base import ConnectionHandler
from app.services.connection_handlers.lambda_cloudwatch import LambdaCloudWatchHandler
from app.services.connection_handlers.lambda_dynamodb import LambdaDynamoDBHandler
from app.services.connection_handlers.lambda_s3 import LambdaS3Handler
from app.services.connection_handlers.lambda_sns import LambdaSNSHandler
from app.services.connection_handlers.lambda_sqs import LambdaSQSHandler
from app.services.connection_handlers.sns_lambda import SNSLambdaHandler
from app.services.connection_handlers.sns_sqs import SNSSQSHandler
from app.services.connection_handlers.sqs_lambda import SQSLambdaHandler

CONNECTION_HANDLER_REGISTRY: dict[tuple[ServiceType, ServiceType], ConnectionHandler] = {
    (ServiceType.API_GATEWAY, ServiceType.LAMBDA): ApiGatewayLambdaHandler(),
    (ServiceType.LAMBDA, ServiceType.DYNAMODB): LambdaDynamoDBHandler(),
    (ServiceType.LAMBDA, ServiceType.S3): LambdaS3Handler(),
    (ServiceType.LAMBDA, ServiceType.CLOUDWATCH): LambdaCloudWatchHandler(),
    (ServiceType.LAMBDA, ServiceType.SNS): LambdaSNSHandler(),
    (ServiceType.LAMBDA, ServiceType.SQS): LambdaSQSHandler(),
    (ServiceType.SQS, ServiceType.LAMBDA): SQSLambdaHandler(),
    (ServiceType.SNS, ServiceType.SQS): SNSSQSHandler(),
    (ServiceType.SNS, ServiceType.LAMBDA): SNSLambdaHandler(),
}
