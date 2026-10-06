"""Certificate roles for a mutual-TLS Client VPN endpoint."""

from typing import Literal

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry


class ClientVpnCertificateConfig(BaseConnectionConfig):
    certificate_role: Literal["server", "client_trust", "both"] = ConnectionField(
        "server",
        label="Certificate role",
        type="select",
        description="Client trust uses the certificate's issuing CA; client certificates must be provisioned separately",
        options=[
            OptionEntry(value="server", label="Server certificate"),
            OptionEntry(value="client_trust", label="Client CA reference"),
            OptionEntry(value="both", label="Server and client CA reference"),
        ],
    )
