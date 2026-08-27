"""Connection registry — the single source of truth for which connections exist."""

from dataclasses import dataclass

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs.configs import (
    ApiGatewayAuthorizerConfig,
    ApiGatewayRouteHandlerConfig,
    DynamoDBLambdaConfig,
    EmptyConnectionConfig,
    EventBridgeTargetConfig,
    LambdaDynamoDBConfig,
    LambdaS3Config,
    S3LambdaConfig,
    SqsLambdaConfig,
)
from app.models.input_models import ServiceType
from app.services.connection_handlers.apigw_lambda import ApiGatewayLambdaHandler
from app.services.connection_handlers.base import ConnectionHandler
from app.services.connection_handlers.dynamodb_lambda import DynamoDBLambdaHandler
from app.services.connection_handlers.eventbridge_targets import (
    EventBridgeLambdaHandler,
    EventBridgeSQSHandler,
)
from app.services.connection_handlers.iam_grant import IamGrantHandler
from app.services.connection_handlers.lambda_cloudwatch import LambdaCloudWatchHandler
from app.services.connection_handlers.s3_lambda import S3LambdaHandler
from app.services.connection_handlers.sns_lambda import SNSLambdaHandler
from app.services.connection_handlers.sns_sqs import SNSSQSHandler
from app.services.connection_handlers.sqs_lambda import SQSLambdaHandler
from app.services.connection_handlers.vpc_membership import VpcMembershipHandler


@dataclass(frozen=True)
class ConnectionSpec:
    """Everything the system knows about one kind of connection."""

    source: ServiceType
    target: ServiceType
    connection_type: str
    label: str
    config_model: type[BaseConnectionConfig]
    handler: ConnectionHandler
    # Chosen when a payload does not name a connection_type for this pair
    is_default: bool = True

    @property
    def key(self) -> tuple[ServiceType, ServiceType, str]:
        return (self.source, self.target, self.connection_type)


CONNECTION_SPECS: list[ConnectionSpec] = [
    ConnectionSpec(
        source=ServiceType.VPC,
        target=ServiceType.SUBNET,
        connection_type="contains",
        label="VPC → Subnet",
        config_model=EmptyConnectionConfig,
        handler=VpcMembershipHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.VPC,
        target=ServiceType.SECURITY_GROUP,
        connection_type="contains",
        label="VPC → Security Group",
        config_model=EmptyConnectionConfig,
        handler=VpcMembershipHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.API_GATEWAY,
        target=ServiceType.LAMBDA,
        connection_type="route_handler",
        label="API Gateway → Lambda (route handler)",
        config_model=ApiGatewayRouteHandlerConfig,
        handler=ApiGatewayLambdaHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.API_GATEWAY,
        target=ServiceType.LAMBDA,
        connection_type="authorizer",
        label="API Gateway → Lambda (authorizer)",
        config_model=ApiGatewayAuthorizerConfig,
        handler=ApiGatewayLambdaHandler(),
        is_default=False,
    ),
    ConnectionSpec(
        source=ServiceType.LAMBDA,
        target=ServiceType.DYNAMODB,
        connection_type="accesses",
        label="Lambda → DynamoDB",
        config_model=LambdaDynamoDBConfig,
        handler=IamGrantHandler(ServiceType.DYNAMODB),
    ),
    ConnectionSpec(
        source=ServiceType.LAMBDA,
        target=ServiceType.S3,
        connection_type="accesses",
        label="Lambda → S3",
        config_model=LambdaS3Config,
        handler=IamGrantHandler(ServiceType.S3),
    ),
    ConnectionSpec(
        source=ServiceType.LAMBDA,
        target=ServiceType.CLOUDWATCH,
        connection_type="logs_to",
        label="Lambda → CloudWatch",
        config_model=EmptyConnectionConfig,
        handler=LambdaCloudWatchHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.LAMBDA,
        target=ServiceType.SNS,
        connection_type="publishes_to",
        label="Lambda → SNS",
        config_model=EmptyConnectionConfig,
        handler=IamGrantHandler(ServiceType.SNS, access_pattern="full"),
    ),
    ConnectionSpec(
        source=ServiceType.LAMBDA,
        target=ServiceType.SQS,
        connection_type="sends_to",
        label="Lambda → SQS",
        config_model=EmptyConnectionConfig,
        handler=IamGrantHandler(ServiceType.SQS, access_pattern="write"),
    ),
    ConnectionSpec(
        source=ServiceType.S3,
        target=ServiceType.LAMBDA,
        connection_type="notifies",
        label="S3 → Lambda",
        config_model=S3LambdaConfig,
        handler=S3LambdaHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.DYNAMODB,
        target=ServiceType.LAMBDA,
        connection_type="streams_to",
        label="DynamoDB Streams → Lambda",
        config_model=DynamoDBLambdaConfig,
        handler=DynamoDBLambdaHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.ECS,
        target=ServiceType.DYNAMODB,
        connection_type="accesses",
        label="ECS → DynamoDB",
        config_model=LambdaDynamoDBConfig,
        handler=IamGrantHandler(ServiceType.DYNAMODB),
    ),
    ConnectionSpec(
        source=ServiceType.ECS,
        target=ServiceType.S3,
        connection_type="accesses",
        label="ECS → S3",
        config_model=LambdaS3Config,
        handler=IamGrantHandler(ServiceType.S3),
    ),
    ConnectionSpec(
        source=ServiceType.EVENTBRIDGE,
        target=ServiceType.LAMBDA,
        connection_type="targets",
        label="EventBridge → Lambda",
        config_model=EventBridgeTargetConfig,
        handler=EventBridgeLambdaHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.EVENTBRIDGE,
        target=ServiceType.SQS,
        connection_type="targets",
        label="EventBridge → SQS",
        config_model=EventBridgeTargetConfig,
        handler=EventBridgeSQSHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.SQS,
        target=ServiceType.LAMBDA,
        connection_type="triggers",
        label="SQS → Lambda",
        config_model=SqsLambdaConfig,
        handler=SQSLambdaHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.SNS,
        target=ServiceType.SQS,
        connection_type="delivers_to",
        label="SNS → SQS",
        config_model=EmptyConnectionConfig,
        handler=SNSSQSHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.SNS,
        target=ServiceType.LAMBDA,
        connection_type="triggers",
        label="SNS → Lambda",
        config_model=EmptyConnectionConfig,
        handler=SNSLambdaHandler(),
    ),
]

CONNECTION_REGISTRY: dict[tuple[ServiceType, ServiceType, str], ConnectionSpec] = {
    spec.key: spec for spec in CONNECTION_SPECS
}

# Derived so a registered connection is legal by construction
COMPATIBLE_CONNECTIONS: set[tuple[ServiceType, ServiceType]] = {
    (spec.source, spec.target) for spec in CONNECTION_SPECS
}


def resolve_spec(
    source: ServiceType, target: ServiceType, connection_type: str, config: dict
) -> ConnectionSpec | None:
    """Find the spec for a connection, tolerating payloads that do not name a type."""
    exact = CONNECTION_REGISTRY.get((source, target, connection_type))
    if exact is not None:
        return exact

    # Older payloads carried the API Gateway role inside connection_config
    role = config.get("connection_role")
    if role:
        by_role = CONNECTION_REGISTRY.get((source, target, role))
        if by_role is not None:
            return by_role

    candidates = [
        s for s in CONNECTION_SPECS if s.source == source and s.target == target
    ]
    if len(candidates) == 1:
        return candidates[0]
    return next((s for s in candidates if s.is_default), None)
