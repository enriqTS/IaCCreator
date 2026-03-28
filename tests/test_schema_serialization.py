# Feature: enhanced-variable-configuration, Property 1: Schema serialization round-trip
"""Property test: VariableSchemaEntry serialization round-trip.

For any valid VariableSchemaEntry (including entries with map/list types, nested
options, validation rules, and visible_when conditions), serializing to JSON via
model_dump() and deserializing back via VariableSchemaEntry(**data) shall produce
an object equal to the original.

**Validates: Requirements 9.2, 9.3, 9.4**
"""

from hypothesis import given, settings, strategies as st

from app.generators.variable_schemas import (
    OptionEntry,
    ValidationRule,
    VariableSchemaEntry,
    VisibleWhen,
)

# ---------------------------------------------------------------------------
# Hypothesis strategies for schema model components
# ---------------------------------------------------------------------------

# Scalar values that can appear in option values, defaults, visible_when equals, etc.
_scalar_st = st.one_of(
    st.text(min_size=1, max_size=20),
    st.integers(min_value=-1000, max_value=1000),
    st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
    st.booleans(),
)

_option_entry_st = st.builds(
    OptionEntry,
    value=_scalar_st,
    label=st.text(min_size=1, max_size=30),
)

_validation_rule_st = st.builds(
    ValidationRule,
    min=st.one_of(st.none(), st.integers(min_value=0, max_value=10000), st.floats(allow_nan=False, allow_infinity=False, min_value=0, max_value=1e4)),
    max=st.one_of(st.none(), st.integers(min_value=0, max_value=100000), st.floats(allow_nan=False, allow_infinity=False, min_value=0, max_value=1e5)),
    pattern=st.one_of(st.none(), st.text(min_size=1, max_size=30)),
    pattern_description=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    allowed_values=st.one_of(st.none(), st.lists(_scalar_st, min_size=1, max_size=5)),
)

_visible_when_st = st.builds(
    VisibleWhen,
    field=st.from_regex(r"[a-z][a-z0-9_]{0,14}", fullmatch=True),
    equals=_scalar_st,
)

_variable_schema_entry_st = st.builds(
    VariableSchemaEntry,
    name=st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True),
    type=st.sampled_from(["string", "number", "bool", "map", "list"]),
    description=st.text(min_size=1, max_size=80),
    default=st.one_of(st.none(), _scalar_st),
    group=st.text(min_size=1, max_size=20),
    options=st.one_of(st.none(), st.lists(_option_entry_st, min_size=1, max_size=5)),
    validation=st.one_of(st.none(), _validation_rule_st),
    visible_when=st.one_of(st.none(), _visible_when_st),
)


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------

@given(entry=_variable_schema_entry_st)
@settings(max_examples=100)
def test_schema_serialization_roundtrip(entry: VariableSchemaEntry) -> None:
    """Serializing a VariableSchemaEntry via model_dump() then deserializing
    back via VariableSchemaEntry(**data) produces an equal object."""
    data = entry.model_dump()
    restored = VariableSchemaEntry(**data)
    assert restored == entry


# Feature: enhanced-variable-configuration, Property 4: All schema entries have a group
# **Validates: Requirements 3.1**

import pytest

from app.generators.variable_schemas import VARIABLE_SCHEMAS
from app.models.input_models import ServiceType


@pytest.mark.parametrize(
    "service_type,entry",
    [
        (st, entry)
        for st in VARIABLE_SCHEMAS
        for entry in VARIABLE_SCHEMAS[st]
    ],
    ids=lambda val: val.value if isinstance(val, ServiceType) else val.name,
)
def test_all_schema_entries_have_a_group(service_type: ServiceType, entry: VariableSchemaEntry) -> None:
    """Every entry in VARIABLE_SCHEMAS must have a non-empty group string."""
    assert isinstance(entry.group, str), (
        f"{service_type.value}.{entry.name}: group must be a string, got {type(entry.group)}"
    )
    assert len(entry.group.strip()) > 0, (
        f"{service_type.value}.{entry.name}: group must be a non-empty string"
    )
