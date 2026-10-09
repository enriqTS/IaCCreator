"""Control-plane log selections map directly to the five native EKS log types."""

from pydantic import StrictBool, model_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField

LOG_TYPES = ("api", "audit", "authenticator", "controllerManager", "scheduler")


class EksLogsConfig(BaseConnectionConfig):
    api: StrictBool = ConnectionField(True, label="API server logs", type="boolean")
    audit: StrictBool = ConnectionField(True, label="Audit logs", type="boolean")
    authenticator: StrictBool = ConnectionField(
        True, label="Authenticator logs", type="boolean"
    )
    controllerManager: StrictBool = ConnectionField(
        True, label="Controller manager logs", type="boolean"
    )
    scheduler: StrictBool = ConnectionField(
        True, label="Scheduler logs", type="boolean"
    )

    def enabled_types(self) -> list[str]:
        return [name for name in LOG_TYPES if getattr(self, name)]

    @model_validator(mode="after")
    def require_logs(self):
        if not self.enabled_types():
            raise ValueError("Select at least one EKS control-plane log type")
        return self
