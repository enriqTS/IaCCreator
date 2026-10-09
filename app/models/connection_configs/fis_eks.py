"""Pod deletion selects one named deployment in an explicit namespace."""

from pydantic import model_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.connection_configs.fis import SELECTION_MODES
from app.models.input_models._metadata import OptionEntry, ValidationRule

KUBERNETES_NAME_PATTERN = r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
SYSTEM_NAMESPACES = ["kube-system", "kube-public", "kube-node-lease"]


class FisEksConfig(BaseConnectionConfig):
    namespace: str = ConnectionField(
        ...,
        label="Kubernetes namespace",
        description="Existing workload namespace; system namespaces are excluded",
        validation=ValidationRule(pattern=KUBERNETES_NAME_PATTERN),
    )
    deployment_name: str = ConnectionField(
        ...,
        label="Deployment name",
        description="Existing Kubernetes Deployment to target",
        validation=ValidationRule(pattern=KUBERNETES_NAME_PATTERN),
    )
    selection_mode: str = ConnectionField(
        "COUNT(1)",
        label="Pod selection",
        type="select",
        options=[OptionEntry(value=value, label=value) for value in SELECTION_MODES],
        validation=ValidationRule(allowed_values=SELECTION_MODES),
    )

    @model_validator(mode="after")
    def reject_system_namespace(self):
        if self.namespace in SYSTEM_NAMESPACES:
            raise ValueError("Pod deletion cannot target a Kubernetes system namespace")
        return self
