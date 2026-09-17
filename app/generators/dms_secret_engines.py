"""Secret endpoint engine and TLS settings are independent of IAM login support."""

from dataclasses import dataclass
from typing import Literal

from app.models.input_models import ServiceType


@dataclass(frozen=True)
class DmsSecretEngine:
    engine_name: str
    ssl_mode: Literal["verify-ca", "verify-full"] = "verify-ca"


DMS_SECRET_ENGINES = {
    ServiceType.RDS: {
        "mysql": DmsSecretEngine("mysql"),
        "mariadb": DmsSecretEngine("mariadb"),
        "postgres": DmsSecretEngine("postgres"),
        "sqlserver-ee": DmsSecretEngine("sqlserver", "verify-full"),
        "sqlserver-se": DmsSecretEngine("sqlserver", "verify-full"),
        "oracle-ee": DmsSecretEngine("oracle"),
        "oracle-se2": DmsSecretEngine("oracle"),
        "oracle-ee-cdb": DmsSecretEngine("oracle"),
        "oracle-se2-cdb": DmsSecretEngine("oracle"),
    },
    ServiceType.AURORA: {
        "aurora-mysql": DmsSecretEngine("aurora"),
        "aurora-postgresql": DmsSecretEngine("aurora-postgresql"),
    },
}
