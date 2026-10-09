"""ECS service tasks resolve at execution time with an explicit selection mode."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.connection_configs.fis import SELECTION_MODES
from app.models.input_models._metadata import OptionEntry, ValidationRule


class FisEcsConfig(BaseConnectionConfig):
    selection_mode: str = ConnectionField(
        "COUNT(1)",
        label="Running task selection",
        type="select",
        options=[OptionEntry(value=value, label=value) for value in SELECTION_MODES],
        validation=ValidationRule(allowed_values=SELECTION_MODES),
    )
