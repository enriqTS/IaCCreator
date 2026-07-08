"""Property-based and complementary tests for backend schema validation.

# Feature: enhanced-variable-configuration, Property 9: Backend validation rejects invalid values
"""

import pytest
from fastapi import HTTPException
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.generators.schema_validator import validate_config_against_schema
from app.generators.variable_schemas import VARIABLE_SCHEMAS
from app.models.input_models import ServiceType
from app.models.input_models._general import get_service_config_models

# ---------------------------------------------------------------------------
# Helpers: collect variables that have validation rules
# ---------------------------------------------------------------------------

# Each entry: (service_type, variable_name, validation_rule, visible_when, config_cls)
_VALIDATED_VARS: list[tuple[ServiceType, str, object, object, type]] = []

_SERVICE_CONFIG_MODELS = get_service_config_models()

for _stype, _entries in VARIABLE_SCHEMAS.items():
    _config_cls = _SERVICE_CONFIG_MODELS.get(_stype)
    if _config_cls is None:
        continue
    _config_fields = set(_config_cls.model_fields.keys())
    for _entry in _entries:
        if _entry.validation is not None:
            # Only include rules that have numeric bounds or allowed_values
            rule = _entry.validation
            if (
                rule.min is not None
                or rule.max is not None
                or rule.allowed_values is not None
            ):
                # Only include if the variable maps to a real config field
                if _entry.name in _config_fields:
                    _VALIDATED_VARS.append(
                        (_stype, _entry.name, rule, _entry.visible_when, _config_cls)
                    )


# ---------------------------------------------------------------------------
# Strategy: generate a value OUTSIDE the valid range for a given rule
# ---------------------------------------------------------------------------


@st.composite
def invalid_value_for_rule(draw, rule):
    """Generate a value that violates the given ValidationRule."""
    if rule.allowed_values is not None:
        # Generate an integer NOT in the allowed set
        val = draw(st.integers(min_value=-1000, max_value=100000))
        assume(val not in rule.allowed_values)
        return val

    if rule.min is not None and rule.max is not None:
        # Pick below min or above max
        below = st.integers(max_value=int(rule.min) - 1)
        above = st.integers(
            min_value=int(rule.max) + 1, max_value=int(rule.max) + 100000
        )
        return draw(st.one_of(below, above))

    if rule.min is not None:
        return draw(st.integers(max_value=int(rule.min) - 1))

    if rule.max is not None:
        return draw(
            st.integers(min_value=int(rule.max) + 1, max_value=int(rule.max) + 100000)
        )

    # Fallback — shouldn't happen for our current schemas
    return draw(st.integers())


# ---------------------------------------------------------------------------
# Property 9: Backend validation rejects invalid values
# **Validates: Requirements 4.10, 8.4**
# ---------------------------------------------------------------------------


@given(data=st.data())
@settings(max_examples=100)
def test_backend_rejects_invalid_values(data):
    """Property 9: For any typed config with a value outside validation bounds,
    validate_config_against_schema raises HTTPException with status_code 422.

    **Validates: Requirements 4.10, 8.4**
    """
    # Pick a random validated variable
    stype, var_name, rule, visible_when, config_cls = data.draw(
        st.sampled_from(_VALIDATED_VARS)
    )

    # Generate an invalid value for this variable's rule
    bad_value = data.draw(invalid_value_for_rule(rule))

    # Build config kwargs — set the invalid field, plus satisfy visible_when if needed
    config_kwargs: dict = {var_name: bad_value}

    if visible_when is not None:
        # Set the discriminating field so the variable IS visible (and thus validated)
        config_kwargs[visible_when.field] = visible_when.equals

    # Provide required fields for services that need them
    if stype == ServiceType.LAMBDA:
        config_kwargs.setdefault("function_name", "test-func")
    if stype == ServiceType.DYNAMODB:
        config_kwargs.setdefault("table_name", "test-table")
        config_kwargs.setdefault("hash_key", "pk")
        config_kwargs.setdefault("hash_key_type", "S")
    if stype == ServiceType.API_GATEWAY:
        config_kwargs.setdefault("api_name", "test-api")
        config_kwargs.setdefault("protocol_type", "HTTP")

    config = config_cls(**config_kwargs)

    with pytest.raises(HTTPException) as exc_info:
        validate_config_against_schema(stype, config)

    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Complementary: valid values do NOT raise exceptions
# ---------------------------------------------------------------------------


@given(data=st.data())
@settings(max_examples=100)
def test_valid_values_do_not_raise(data):
    """Complementary test: valid values within bounds do not raise HTTPException."""
    stype, var_name, rule, visible_when, config_cls = data.draw(
        st.sampled_from(_VALIDATED_VARS)
    )

    # Generate a valid value
    if rule.allowed_values is not None:
        good_value = data.draw(st.sampled_from(rule.allowed_values))
    elif rule.min is not None and rule.max is not None:
        good_value = data.draw(
            st.integers(min_value=int(rule.min), max_value=int(rule.max))
        )
    elif rule.min is not None:
        good_value = data.draw(
            st.integers(min_value=int(rule.min), max_value=int(rule.min) + 10000)
        )
    elif rule.max is not None:
        good_value = data.draw(st.integers(min_value=0, max_value=int(rule.max)))
    else:
        good_value = data.draw(st.integers())

    config_kwargs: dict = {var_name: good_value}

    if visible_when is not None:
        config_kwargs[visible_when.field] = visible_when.equals

    # Provide required fields for services that need them
    if stype == ServiceType.LAMBDA:
        config_kwargs.setdefault("function_name", "test-func")
    if stype == ServiceType.DYNAMODB:
        config_kwargs.setdefault("table_name", "test-table")
        config_kwargs.setdefault("hash_key", "pk")
        config_kwargs.setdefault("hash_key_type", "S")
    if stype == ServiceType.API_GATEWAY:
        config_kwargs.setdefault("api_name", "test-api")
        config_kwargs.setdefault("protocol_type", "HTTP")

    config = config_cls(**config_kwargs)

    # Should NOT raise
    validate_config_against_schema(stype, config)
