"""A representative architecture exercising every wired connection type."""

from __future__ import annotations

from app.generators.module_paths import instance_module_dir
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
from app.models.input_models.ecs_config import EcsConfig
from app.models.input_models.eventbridge_config import EventBridgeConfig
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
            filename="lambda.zip",
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
        _lambda("on-upload"),
        _lambda("on-change"),
        ResourceInstance(
            name="worker",
            service_type=ServiceType.ECS,
            config=EcsConfig(cluster_name="worker"),
        ),
        ResourceInstance(
            name="users",
            service_type=ServiceType.DYNAMODB,
            config=DynamoDBConfig(
                table_name="users",
                hash_key="id",
                hash_key_type="S",
                billing_mode="PAY_PER_REQUEST",
                stream_enabled=True,
                stream_view_type="NEW_AND_OLD_IMAGES",
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
            name="alerts",
            service_type=ServiceType.SNS,
            config=SnsConfig(topic_name="alerts"),
        ),
        ResourceInstance(
            name="audit",
            service_type=ServiceType.SQS,
            config=SqsConfig(queue_name="audit"),
        ),
        ResourceInstance(
            name="nightly",
            service_type=ServiceType.EVENTBRIDGE,
            config=EventBridgeConfig(
                rule_name="nightly",
                schedule_expression="rate(1 day)",
                state="ENABLED",
            ),
        ),
        ResourceInstance(
            name="app-logs",
            service_type=ServiceType.CLOUDWATCH,
            config=CloudWatchConfig(log_group_name="app-logs"),
        ),
    ]

    connections = [
        Connection(
            source="public-api", target="create-user", connection_type="route_handler"
        ),
        Connection(
            source="public-api", target="list-users", connection_type="route_handler"
        ),
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
        Connection(
            source="create-user", target="events", connection_type="publishes_to"
        ),
        Connection(source="create-user", target="jobs", connection_type="sends_to"),
        Connection(source="events", target="jobs", connection_type="delivers_to"),
        # Fan-in: a second topic delivering to the same queue
        Connection(source="alerts", target="jobs", connection_type="delivers_to"),
        # Fan-out: the same topic delivering to a second queue
        Connection(source="events", target="audit", connection_type="delivers_to"),
        # One rule fanning out to targets of different service types
        Connection(
            source="nightly",
            target="process-job",
            connection_type="targets",
            connection_config={"target_id": "nightly-processor"},
        ),
        Connection(source="nightly", target="audit", connection_type="targets"),
        Connection(source="events", target="process-job", connection_type="triggers"),
        Connection(
            source="uploads",
            target="on-upload",
            connection_type="notifies",
            connection_config={
                "events": ["s3:ObjectCreated:*"],
                "filter_suffix": ".csv",
            },
        ),
        Connection(
            source="users",
            target="on-change",
            connection_type="streams_to",
            connection_config={"starting_position": "LATEST", "batch_size": 50},
        ),
        Connection(
            source="worker",
            target="users",
            connection_type="accesses",
            connection_config={"access_pattern": "read"},
        ),
        Connection(
            source="worker",
            target="uploads",
            connection_type="accesses",
            connection_config={"access_pattern": "write"},
        ),
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
    """Connection files for the colliding-route architecture."""
    return _connection_files(colliding_route_architecture())


def reference_ir() -> ProjectIR:
    """Build the IR for the reference architecture."""
    return IRBuilder().build(reference_architecture())


def reference_tree() -> FileTree:
    """Generate the full file tree for the reference architecture."""
    return CodeGenerator().generate(reference_ir())


def _connection_files(architecture: ArchitectureDescription) -> list[GeneratedFile]:
    """Resolve connection resources to tree paths, before merging can hide collisions."""
    project = IRBuilder().build(architecture)
    contribution = ConnectionProcessor().process_all(project)
    instances = {i.name: i for m in project.modules for i in m.instances}
    return [
        GeneratedFile(
            path=f"{instance_module_dir(project.project_name, instances[r.module])}/{r.filename}",
            content=r.content,
        )
        for r in contribution.resources
        if r.module in instances
    ]


def reference_connection_files() -> list[GeneratedFile]:
    """Connection-produced files for the reference architecture."""
    return _connection_files(reference_architecture())
