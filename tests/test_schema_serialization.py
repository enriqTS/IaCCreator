"""Round-trip and structural invariants for the variable schema models."""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.input_models._metadata import (
    OptionEntry,
    ValidationRule,
    VariableSchemaEntry,
    VisibleWhen,
)
from tests.schema_helpers import service_schemas

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
    min=st.one_of(
        st.none(),
        st.integers(min_value=0, max_value=10000),
        st.floats(allow_nan=False, allow_infinity=False, min_value=0, max_value=1e4),
    ),
    max=st.one_of(
        st.none(),
        st.integers(min_value=0, max_value=100000),
        st.floats(allow_nan=False, allow_infinity=False, min_value=0, max_value=1e5),
    ),
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


@given(entry=_variable_schema_entry_st)
@settings(max_examples=100)
def test_schema_serialization_roundtrip(entry: VariableSchemaEntry) -> None:
    """model_dump() then VariableSchemaEntry(**data) must reproduce the original."""
    data = entry.model_dump()
    assert VariableSchemaEntry(**data) == entry


def test_all_schema_entries_have_a_group() -> None:
    """The editor groups fields into sections, so an ungrouped entry cannot render."""
    schemas = service_schemas()
    ungrouped = [
        f"{service_type.value}.{entry.name}"
        for service_type in schemas
        for entry in schemas[service_type]
        if not isinstance(entry.group, str) or not entry.group.strip()
    ]
    assert not ungrouped, "Schema entries with a missing or empty group:\n" + "\n".join(
        ungrouped
    )
