"""Share endpoint identity rules across authentication methods."""

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR

ENDPOINT_KINDS = {
    "source_endpoint",
    "target_endpoint",
    "source_secret_endpoint",
    "target_secret_endpoint",
}


def validate_endpoint_identity(
    connection: ConnectionIR, project: ProjectIR, endpoint_id: str
) -> None:
    for other in project.connections:
        if (
            other.source_service == ServiceType.DATABASE_MIGRATION_SERVICE
            and other.connection_type in ENDPOINT_KINDS
            and other.connection_config.get("endpoint_id") == endpoint_id
            and (
                other.source_name,
                other.target_name,
                other.connection_type,
                other.connection_config,
            )
            != (
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                connection.connection_config,
            )
        ):
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("dms",),
                        "msg": "DMS endpoint identifiers must be unique across this project",
                    }
                ],
            )
