"""Connection-derived inputs schema — declares inputs that come from service connections.

Each per-service config can override `get_connections_schema()` to declare which
inputs it receives from connections to other services. For example, API Gateway
might receive `lambda_invoke_arn` from an APIGW→Lambda connection.

These are NOT user-editable Terraform variables — they are derived at generation
time from the architecture's connection graph.
"""

from __future__ import annotations

from pydantic import BaseModel


class ConnectionInput(BaseModel):
    """A single connection-derived input for a service.

    Attributes:
        name: Logical name of the input (e.g., "lambda_invoke_arn").
        source_service_type: The service type string this input comes from (e.g., "lambda").
        description: Human-readable description of what this input provides.
        tf_variable_name: The Terraform variable name emitted for this input.
        connection_role: Optional role qualifier when multiple connections of the
            same type exist (e.g., "route_handler" vs "authorizer" for Lambda→APIGW).
    """

    name: str
    source_service_type: str
    description: str
    tf_variable_name: str
    connection_role: str | None = None
