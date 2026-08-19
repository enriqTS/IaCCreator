"""A representative architecture exercising every wired connection type."""

from __future__ import annotations

from app.models.input_models import (
    ArchitectureDescription,
    Connection,
    EnvironmentConfig,
    ResourceInstance,
    ServiceType,
)
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.input_models.cloudwatch_config import CloudWatchConfig
from app.models.input_models.dynamodb_config import DynamoDBConfig
from app.models.input_models.lambda_config import LambdaConfig
from app.models.input_models.s3_config import S3Config
from app.models.input_models.sns_config import SnsConfig
from app.models.input_models.sqs_config import SqsConfig
from app.models.ir_models import FileTree, GeneratedFile, ProjectIR
from app.services.code_generator import CodeGenerator
from app.services.connection_processor import ConnectionProcessor
from app.services.ir_builder import IRBuilder

PROJECT_NAME = "reference-project"

ENVIRONMENTS = ("dev", "prod")


def _lambda(name: str) -> ResourceInstance:
    return ResourceInstance(
        name=name,
        service_type=ServiceType.LAMBDA,
        config=LambdaConfig(
            function_name=name,
            handler="index.handler",
            runtime="python3.12",
        ),
    )


def reference_architecture() -> ArchitectureDescription:
    """Build an architecture covering every pair in the connection handler registry."""
    gateway = ResourceInstance(
        name="public-api",
        service_type=ServiceType.API_GATEWAY,
        config=ApiGatewayConfig(
            api_name="public-api",
            protocol_type="HTTP",
            routes=[
                {
                    "methods": ["POST"],
                    "path": "/users",
                    "integration_name": "create-user",
                },
                {
                    "methods": ["GET"],
                    "path": "/users/{id}",
                    "integration_name": "list-users",
                },
            ],
        ),
    )

    resources = [
        gateway,
        _lambda("create-user"),
        _lambda("list-users"),
        _lambda("process-job"),
        ResourceInstance(
            name="users",
            service_type=ServiceType.DYNAMODB,
            config=DynamoDBConfig(
                table_name="users",
                hash_key="id",
                hash_key_type="S",
                billing_mode="PAY_PER_REQUEST",
            ),
        ),
        ResourceInstance(
            name="uploads",
            service_type=ServiceType.S3,
            config=S3Config(bucket_name="uploads"),
        ),
        ResourceInstance(
            name="jobs",
            service_type=ServiceType.SQS,
            config=SqsConfig(queue_name="jobs"),
        ),
        ResourceInstance(
            name="events",
            service_type=ServiceType.SNS,
            config=SnsConfig(topic_name="events"),
        ),
        ResourceInstance(
            name="app-logs",
            service_type=ServiceType.CLOUDWATCH,
            config=CloudWatchConfig(log_group_name="app-logs"),
        ),
    ]

    connections = [
        Connection(source="public-api", target="create-user", connection_type="route_handler"),
        Connection(source="public-api", target="list-users", connection_type="route_handler"),
        Connection(
            source="create-user",
            target="users",
            connection_type="writes_to",
            connection_config={"access_pattern": "full"},
        ),
        Connection(
            source="list-users",
            target="users",
            connection_type="reads_from",
            connection_config={"access_pattern": "read"},
        ),
        Connection(
            source="create-user",
            target="uploads",
            connection_type="writes_to",
            connection_config={"access_pattern": "write"},
        ),
        Connection(source="create-user", target="app-logs", connection_type="logs_to"),
        Connection(source="create-user", target="events", connection_type="publishes_to"),
        Connection(source="create-user", target="jobs", connection_type="sends_to"),
        Connection(source="events", target="jobs", connection_type="delivers_to"),
        Connection(source="events", target="process-job", connection_type="triggers"),
        Connection(
            source="jobs",
            target="process-job",
            connection_type="triggers",
            connection_config={"batch_size": 5},
        ),
    ]

    return ArchitectureDescription(
        project_name=PROJECT_NAME,
        environments=[EnvironmentConfig(name=name) for name in ENVIRONMENTS],
        resources=resources,
        connections=connections,
    )


def colliding_route_architecture() -> ArchitectureDescription:
    """Two routes differing only in whether a segment is a path parameter."""
    return ArchitectureDescription(
        project_name=PROJECT_NAME,
        environments=[EnvironmentConfig(name="dev")],
        resources=[
            ResourceInstance(
                name="public-api",
                service_type=ServiceType.API_GATEWAY,
                config=ApiGatewayConfig(
                    api_name="public-api",
                    protocol_type="HTTP",
                    routes=[
                        {
                            "methods": ["GET"],
                            "path": "/users/{id}",
                            "integration_name": "handler",
                        },
                        {
                            "methods": ["GET"],
                            "path": "/users/id",
                            "integration_name": "handler",
                        },
                    ],
                ),
            ),
            _lambda("handler"),
        ],
        connections=[
            Connection(
                source="public-api", target="handler", connection_type="route_handler"
            )
        ],
    )


def colliding_route_connection_files() -> list[GeneratedFile]:
    """Return connection files for the colliding-route architecture."""
    return ConnectionProcessor().process_all(IRBuilder().build(colliding_route_architecture()))


def reference_ir() -> ProjectIR:
    """Build the IR for the reference architecture."""
    return IRBuilder().build(reference_architecture())


def reference_tree() -> FileTree:
    """Generate the full file tree for the reference architecture."""
    return CodeGenerator().generate(reference_ir())


def reference_connection_files() -> list[GeneratedFile]:
    """Return the files produced by connection processing, before tree merging hides collisions."""
    return ConnectionProcessor().process_all(reference_ir())
