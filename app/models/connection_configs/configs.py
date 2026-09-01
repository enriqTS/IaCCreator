"""Typed configuration for every supported connection kind."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import (
    ConnectionField,
    LinkedEntry,
    LinkedEntryField,
)
from app.models.input_models._metadata import OptionEntry, ValidationRule
from app.models.input_models.api_gateway_route import HTTP_METHODS

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
            entry_fields=[
                LinkedEntryField(
                    key="methods",
                    label="Methods",
                    type="multiSelect",
                    default=["ANY"],
                    options=[OptionEntry(value=m, label=m) for m in HTTP_METHODS],
                    exclusive_options=["ANY"],
                )
            ],
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


class S3LambdaConfig(BaseConnectionConfig):
    """An S3 bucket notifying a Lambda when objects change."""

    events: list[str] = ConnectionField(
        default_factory=lambda: ["s3:ObjectCreated:*"],
        label="Events",
        description="Object events that invoke the function",
        type="multiSelect",
        options=[
            OptionEntry(value="s3:ObjectCreated:*", label="Object created"),
            OptionEntry(value="s3:ObjectRemoved:*", label="Object removed"),
            OptionEntry(value="s3:ObjectRestore:*", label="Object restored"),
        ],
    )
    filter_prefix: str | None = ConnectionField(
        None,
        label="Key Prefix",
        description="Only notify for keys starting with this prefix",
        placeholder="Optional, e.g. uploads/",
    )
    filter_suffix: str | None = ConnectionField(
        None,
        label="Key Suffix",
        description="Only notify for keys ending with this suffix",
        placeholder="Optional, e.g. .jpg",
    )


class DynamoDBLambdaConfig(BaseConnectionConfig):
    """A DynamoDB stream feeding a Lambda."""

    starting_position: str = ConnectionField(
        "LATEST",
        label="Starting Position",
        description="Where in the stream the function begins reading",
        type="select",
        options=[
            OptionEntry(value="LATEST", label="Latest"),
            OptionEntry(value="TRIM_HORIZON", label="Trim horizon (oldest)"),
        ],
        validation=ValidationRule(allowed_values=["LATEST", "TRIM_HORIZON"]),
    )
    batch_size: int = ConnectionField(
        100,
        label="Batch Size",
        description="Stream records delivered per invocation",
        type="number",
        validation=ValidationRule(min=1, max=10000),
    )
    stream_view_type: str = ConnectionField(
        "NEW_AND_OLD_IMAGES",
        label="Stream View Type",
        description="What the table writes to the stream this function reads",
        type="select",
        options=[
            OptionEntry(value="NEW_IMAGE", label="New Image"),
            OptionEntry(value="OLD_IMAGE", label="Old Image"),
            OptionEntry(value="NEW_AND_OLD_IMAGES", label="New and Old Images"),
            OptionEntry(value="KEYS_ONLY", label="Keys Only"),
        ],
        validation=ValidationRule(
            allowed_values=[
                "NEW_IMAGE",
                "OLD_IMAGE",
                "NEW_AND_OLD_IMAGES",
                "KEYS_ONLY",
            ]
        ),
    )


class GatewayRouteConfig(BaseConnectionConfig):
    """A route from a route table through a managed gateway."""

    destination_cidr_block: str = ConnectionField(
        "0.0.0.0/0",
        label="Destination CIDR",
        description="IPv4 network reached through this gateway",
        validation=ValidationRule(
            pattern=r"^(?:\d{1,3}\.){3}\d{1,3}/(?:[0-9]|[12][0-9]|3[0-2])$",
            pattern_description="Must be an IPv4 CIDR block",
        ),
    )

    @field_validator("destination_cidr_block")
    @classmethod
    def validate_destination(cls, value: str) -> str:
        from ipaddress import IPv4Network

        try:
            IPv4Network(value, strict=True)
        except ValueError as exc:
            raise ValueError(
                "destination_cidr_block must be an IPv4 network CIDR"
            ) from exc
        return value


class EventBridgeTargetConfig(BaseConnectionConfig):
    """A rule firing at one target."""

    target_id: str | None = ConnectionField(
        None,
        label="Target Id",
        description="Identifier for this target within the rule",
        placeholder="Optional, defaults to the target's name",
        validation=ValidationRule(
            pattern=r"^[\w.\-]{1,64}$",
            pattern_description="Only letters, digits, dots, hyphens and underscores",
        ),
    )
    input: str | None = ConnectionField(
        None,
        label="Constant Input",
        description="JSON passed to the target instead of the matched event",
        placeholder='Optional, e.g. {"source":"scheduler"}',
    )
