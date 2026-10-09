"""Explicit instance targets share one action and bounded selection mode."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry, ValidationRule

SELECTION_MODES = [f"COUNT({count})" for count in range(1, 6)] + ["ALL"]
ACTION_NAME_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class FisEc2Config(BaseConnectionConfig):
    operation: str = ConnectionField(
        "reboot",
        label="Instance fault",
        type="select",
        options=[
            OptionEntry(value="reboot", label="Reboot"),
            OptionEntry(value="stop", label="Stop without automatic restart"),
        ],
        validation=ValidationRule(allowed_values=["reboot", "stop"]),
    )
    selection_mode: str = ConnectionField(
        "COUNT(1)",
        label="Target selection",
        type="select",
        options=[OptionEntry(value=value, label=value) for value in SELECTION_MODES],
        validation=ValidationRule(allowed_values=SELECTION_MODES),
    )
