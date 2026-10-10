"""Daily associations keep schedule derivation and parameter parsing in the backend."""

import json
import re

from pydantic import StrictBool, StrictInt, field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule

PARAMETER_NAME_PATTERN = r"^[A-Za-z0-9]{1,255}$"
DOCUMENT_NAME_PATTERN = r"^[A-Za-z0-9_.-]{3,128}$"


def string_parameters(content: str) -> dict[str, str]:
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Parameter names must be unique")
            result[key] = value
        return result

    if len(content.encode("utf-8")) > 32768:
        raise ValueError("Association parameters must not exceed 32 KiB")
    try:
        values = json.loads(content, object_pairs_hook=unique_pairs)
    except (ValueError, RecursionError) as exc:
        raise ValueError(
            "Association parameters require a JSON object of strings"
        ) from exc
    if not isinstance(values, dict) or any(
        not re.fullmatch(PARAMETER_NAME_PATTERN, key) or not isinstance(value, str)
        for key, value in values.items()
    ):
        raise ValueError("Association parameters require named string values")
    return dict(sorted(values.items()))


class SsmEc2Config(BaseConnectionConfig):
    utc_hour: StrictInt = ConnectionField(
        3,
        label="Daily hour (UTC)",
        type="number",
        validation=ValidationRule(min=0, max=23),
    )
    utc_minute: StrictInt = ConnectionField(
        0,
        label="Daily minute (UTC)",
        type="number",
        validation=ValidationRule(min=0, max=59),
    )
    apply_immediately: StrictBool = ConnectionField(
        False,
        label="Run on creation or update",
        type="boolean",
        description="Otherwise defer execution until the next daily scheduled time",
    )
    parameters_json: str = ConnectionField(
        "{}",
        label="String parameters (JSON)",
        type="json",
        description="Non-secret String overrides declared by the connected document",
    )

    @field_validator("parameters_json")
    @classmethod
    def validate_parameters(cls, value: str) -> str:
        return json.dumps(string_parameters(value), sort_keys=True, ensure_ascii=False)
