"""Typed configuration for every supported connection kind."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField, LinkedEntry
from app.models.input_models._metadata import OptionEntry, ValidationRule

_ACCESS_PATTERN_VALIDATION = ValidationRule(allowed_values=["read", "write", "full"])


def _access_pattern_options(read: str, write: str) -> list[OptionEntry]:
    return [
        OptionEntry(value="read", label=f"Read Only ({read})"),
        OptionEntry(value="write", label=f"Write Only ({write})"),
        OptionEntry(value="full", label="Full Access (Read + Write)"),
    ]


class EmptyConnectionConfig(BaseConnectionConfig):
    """A connection that needs no user configuration."""


class ApiGatewayRouteHandlerConfig(BaseConnectionConfig):
    """API Gateway routing requests to a Lambda function."""

    route_path: str | None = ConnectionField(
        None,
        label="Route",
        description="Route on the gateway that this function handles",
        type="linkedSelect",
        validation=ValidationRule(
            pattern=r"^/[\w\-/{}\$]*$",
            pattern_description="Must start with / and contain only alphanumerics, /, -, _, {, } or $",
        ),
        linked=LinkedEntry(
            config_path="routes",
            display_key="path",
            create_template={
                "methods": ["ANY"],
                "path": "",
                "integration_name": "",
                "integration_type": "AWS_PROXY",
                "payload_format_version": "2.0",
            },
            target_name_key="integration_name",
            target_id_key="integration_id",
        ),
    )
    integration_type: str = ConnectionField(
        "AWS_PROXY",
        label="Integration Type",
        description="API Gateway integration type",
        type="select",
        options=[OptionEntry(value="AWS_PROXY", label="Lambda Proxy (AWS_PROXY)")],
    )
    payload_format_version: str = ConnectionField(
        "2.0",
        label="Payload Format Version",
        description="Payload format passed to the function",
        type="select",
        options=[
            OptionEntry(value="1.0", label="1.0"),
            OptionEntry(value="2.0", label="2.0"),
        ],
    )
    vpc_link_name: str | None = ConnectionField(
        None,
        label="VPC Link",
        description="Name of a VPC link to route through, if any",
        placeholder="Optional",
    )
    # Derived by the IR builder from the gateway's own routes, never sent by a user
    routes: list[dict[str, Any]] = Field(default_factory=list)


class ApiGatewayAuthorizerConfig(BaseConnectionConfig):
    """A Lambda acting as a REQUEST authorizer for an API Gateway."""

    authorizer_name: str | None = ConnectionField(
        None,
        label="Authorizer Name",
        description="Name given to the authorizer resource",
        validation=ValidationRule(
            pattern=r"^[\w\-]{1,128}$",
            pattern_description="Only alphanumerics, hyphens and underscores (1-128 characters)",
        ),
    )
    payload_format_version: str = ConnectionField(
        "2.0",
        label="Payload Format Version",
        description="Payload format passed to the authorizer",
        type="select",
        options=[
            OptionEntry(value="1.0", label="1.0"),
            OptionEntry(value="2.0", label="2.0"),
        ],
    )


class LambdaDynamoDBConfig(BaseConnectionConfig):
    """A Lambda reading from or writing to a DynamoDB table."""

    access_pattern: str = ConnectionField(
        "full",
        label="Access Pattern",
        description="How much access the function needs to the table",
        type="select",
        options=_access_pattern_options(
            "GetItem, Query, Scan", "PutItem, UpdateItem, DeleteItem"
        ),
        validation=_ACCESS_PATTERN_VALIDATION,
    )


class LambdaS3Config(BaseConnectionConfig):
    """A Lambda reading from or writing to an S3 bucket."""

    access_pattern: str = ConnectionField(
        "full",
        label="Access Pattern",
        description="How much access the function needs to the bucket",
        type="select",
        options=_access_pattern_options(
            "GetObject, ListBucket", "PutObject, DeleteObject"
        ),
        validation=_ACCESS_PATTERN_VALIDATION,
    )


class SqsLambdaConfig(BaseConnectionConfig):
    """An SQS queue triggering a Lambda through an event source mapping."""

    batch_size: int = ConnectionField(
        10,
        label="Batch Size",
        description="Messages delivered to the function per invocation",
        type="number",
        validation=ValidationRule(min=1, max=10000),
    )
    maximum_batching_window_in_seconds: int | None = ConnectionField(
        None,
        label="Batching Window (seconds)",
        description="How long to gather messages before invoking",
        type="number",
        placeholder="Optional (0-300)",
        validation=ValidationRule(min=0, max=300),
    )
