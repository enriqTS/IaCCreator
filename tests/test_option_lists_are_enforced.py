"""An option list is the complete set of valid AWS values, so it must be enforced.

Derived from the models, so a newly added option list is covered automatically.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.generators.schema_validator import validate_config_against_schema
from app.models.input_models import ServiceType
from app.models.input_models._general import get_service_config_models
from app.models.input_models._metadata import get_terraform_meta

# Catalogues AWS keeps growing, where the options stay suggestions
OPEN_OPTION_FIELDS: set[tuple[ServiceType, str]] = {
    (ServiceType.LAMBDA, "runtime"),
    (ServiceType.BEDROCK, "base_model_identifier"),
    (ServiceType.SAGEMAKER, "instance_type"),
    (ServiceType.BEDROCK_AGENT, "foundation_model"),
    (ServiceType.BEDROCK_KNOWLEDGE_BASE, "embedding_model_arn"),
    (ServiceType.BEDROCK_AGENTCORE, "foundation_model"),
}


def _option_fields() -> list[tuple[ServiceType, str, list]]:
    found = []
    for service_type, config_cls in get_service_config_models().items():
        if not config_cls.has_terraform_schema():
            continue
        for name, field in config_cls.model_fields.items():
            meta = get_terraform_meta(field)
            if meta is not None and meta.options:
                found.append((service_type, name, meta.options))
    return found


OPTION_FIELDS = _option_fields()


@pytest.mark.parametrize(
    ("service_type", "name", "options"),
    OPTION_FIELDS,
    ids=[f"{s.value}.{n}" for s, n, _ in OPTION_FIELDS],
)
def test_option_list_constrains_the_field(service_type, name, options) -> None:
    """Every option list is enforced unless the field opts out explicitly."""
    entry = next(
        e for e in type(_config(service_type)).get_variable_schema() if e.name == name
    )
    allowed = entry.validation.allowed_values if entry.validation else None

    if (service_type, name) in OPEN_OPTION_FIELDS:
        assert allowed is None, f"{name} is marked open but is being enforced"
        return

    assert allowed == [option.value for option in options], (
        f"{service_type.value}.{name} renders a dropdown but accepts other values"
    )


def _config(service_type: ServiceType):
    return get_service_config_models()[service_type].model_construct()


def test_an_enforced_field_rejects_a_value_outside_its_options() -> None:
    """The schema validator, not just the schema, has to act on the constraint."""
    from app.models.input_models.s3_config import S3Config

    with pytest.raises(HTTPException) as exc:
        validate_config_against_schema(
            ServiceType.S3, S3Config(bucket_name="b", sse_algorithm="rot13")
        )
    assert exc.value.status_code == 422


def test_a_list_field_rejects_a_single_bad_entry() -> None:
    """List-valued fields are checked per entry, not as a whole value."""
    from app.models.input_models.s3_config import S3Config

    with pytest.raises(HTTPException) as exc:
        validate_config_against_schema(
            ServiceType.S3,
            S3Config(bucket_name="b", cors_allowed_methods=["GET", "YOLO"]),
        )
    assert exc.value.status_code == 422
