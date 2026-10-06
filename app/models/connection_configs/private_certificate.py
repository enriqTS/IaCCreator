"""Key selection for an ACM-managed private certificate."""

from typing import Literal

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry


class PrivateCertificateConfig(BaseConnectionConfig):
    key_algorithm: Literal["AUTO", "RSA_2048", "EC_prime256v1", "EC_secp384r1"] = (
        ConnectionField(
            "AUTO",
            label="Certificate key algorithm",
            type="select",
            description="Automatic selection follows the CA key family; explicit keys must use the same family",
            options=[
                OptionEntry(value="AUTO", label="Automatic"),
                OptionEntry(value="RSA_2048", label="RSA 2048"),
                OptionEntry(value="EC_prime256v1", label="ECDSA P-256"),
                OptionEntry(value="EC_secp384r1", label="ECDSA P-384"),
            ],
        )
    )
