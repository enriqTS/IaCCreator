"""Managed placement lists preserve external identifiers across repeated processing."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.models.input_models import ArchitectureDescription
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.network_placement import ListPlacementHandler
from app.services.connection_handlers.registry import CONNECTION_SPECS
from app.services.connection_processor import ConnectionProcessor
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.hcl_assertions import assert_tree_parses


@pytest.mark.parametrize(
    "spec",
    [
        spec
        for spec in CONNECTION_SPECS
        if isinstance(spec.handler, ListPlacementHandler)
    ],
    ids=lambda spec: f"{spec.source.value}-{spec.target.value}",
)
@given(order=st.permutations([0, 1, 2]))
def test_external_identifiers_survive_converging_connections(spec, order):
    payload = connection_architecture(spec)
    input_name = spec.handler._input_name
    payload["resources"][1]["config"][input_name] = [
        "external-b",
        "external-a",
        "external-a",
    ]
    source = deepcopy(payload["resources"][0])
    source.update(id="other", name="other-source")
    payload["resources"].append(source)
    payload["connections"].append(
        dict(payload["connections"][0], source="other-source", source_id="other")
    )
    payload["connections"].append(dict(payload["connections"][0]))
    baseline = CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(payload))
    )
    payload["connections"] = [payload["connections"][index] for index in order]
    ir = IRBuilder().build(ArchitectureDescription.model_validate(payload))
    contribution = ConnectionProcessor().process_all(ir)
    value = next(item.value for item in contribution.inputs if item.name == input_name)
    assert value.count('"external-a"') == 1
    assert value.count('"external-b"') == 1
    assert "module.other-source." in value
    assert "module.source-resource." in value
    assert "managed-by-connection" not in value
    tree = CodeGenerator().generate(ir)
    assert_tree_parses(tree)
    assert dict(tree) == dict(baseline)
