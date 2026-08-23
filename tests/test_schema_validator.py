"""Property-based and complementary tests for backend schema validation."""

import pytest
from fastapi import HTTPException
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.generators.schema_validator import validate_config_against_schema
from app.models.input_models import ServiceType
from app.models.input_models._general import get_service_config_models
from tests.schema_helpers import service_schemas

# ---------------------------------------------------------------------------
# Helpers: collect variables that have validation rules
# ---------------------------------------------------------------------------

# Each entry: (service_type, variable_name, validation_rule, visible_when, config_cls)
_VALIDATED_VARS: list[tuple[ServiceType, str, object, object, type]] = []

_SERVICE_CONFIG_MODELS = get_service_config_models()

for _stype, _entries in service_schemas().items():
    _config_cls = _SERVICE_CONFIG_MODELS.get(_stype)
    if _config_cls is None:
        continue
    _config_fields = set(_config_cls.model_fields.keys())
    for _entry in _entries:
        if _entry.validation is not None:
            # Only include rules that have numeric bounds or allowed_values
            rule = _entry.validation
            has_bounds = (
                rule.min is not None
                or rule.max is not None
                or rule.allowed_values is not None
            )
            # Only rules that constrain a variable backed by a real config field
            if has_bounds and _entry.name in _config_fields:
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
        # Match the type of the allowed values, so the value is rejected for being
        # out of the set rather than for being the wrong type
        if all(isinstance(v, str) for v in rule.allowed_values):
            val = draw(
                st.text(
                    min_size=1,
                    max_size=12,
                    alphabet=st.characters(whitelist_categories=("L",)),
                )
            )
        else:
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
# ---------------------------------------------------------------------------


# Fields a service needs before its own schema validation is the thing under test
_REQUIRED_FIELDS: dict[ServiceType, dict] = {
    ServiceType.LAMBDA: {"function_name": "test-func"},
    ServiceType.DYNAMODB: {
        "table_name": "test-table",
        "hash_key": "pk",
        "hash_key_type": "S",
    },
    ServiceType.API_GATEWAY: {"api_name": "test-api", "protocol_type": "HTTP"},
    ServiceType.EVENTBRIDGE: {"event_pattern": '{"source": ["aws.s3"]}'},
}


def _apply_required_fields(stype: ServiceType, config_kwargs: dict) -> None:
    """Fill in what a service needs so an unrelated rule does not fire first."""
    for key, value in _REQUIRED_FIELDS.get(stype, {}).items():
        config_kwargs.setdefault(key, value)


@given(data=st.data())
@settings(max_examples=100)
def test_backend_rejects_invalid_values(data):
    """Property 9: For any typed config with a value outside validation bounds,
    validate_config_against_schema raises HTTPException with status_code 422.
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

    _apply_required_fields(stype, config_kwargs)

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

    _apply_required_fields(stype, config_kwargs)

    config = config_cls(**config_kwargs)

    # Should NOT raise
    validate_config_against_schema(stype, config)
