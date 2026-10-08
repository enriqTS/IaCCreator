"""Access logging binds a selected HTTP stage to a managed log group."""

import re

from pydantic import field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField

DEFAULT_ACCESS_LOG_FORMAT = (
    '{"requestId":"$context.requestId",'
    '"ip":"$context.identity.sourceIp",'
    '"requestTime":"$context.requestTime",'
    '"httpMethod":"$context.httpMethod",'
    '"routeKey":"$context.routeKey",'
    '"status":"$context.status",'
    '"protocol":"$context.protocol"}'
)
REQUEST_ID_PATTERN = r"\$context\.requestId([^A-Za-z0-9_]|$)"


class ApiGatewayLogsConfig(BaseConnectionConfig):
    stage_name: str = ConnectionField(
        "",
        label="HTTP API stage",
        description="Empty selects the first configured stage, or the default HTTP stage",
    )
    log_format: str = ConnectionField(
        DEFAULT_ACCESS_LOG_FORMAT,
        label="Access log format",
        description="A single line containing $context.requestId; JSON and text formats are supported",
    )

    @field_validator("stage_name")
    @classmethod
    def validate_stage(cls, value: str) -> str:
        if (
            value
            and value != "$default"
            and not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value)
        ):
            raise ValueError("Use an API stage name or $default")
        return value

    @field_validator("log_format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        if "\n" in value or "\r" in value or not re.search(REQUEST_ID_PATTERN, value):
            raise ValueError(
                "Use a single-line access log format containing $context.requestId"
            )
        return value
