"""Property-based test for diagram save/load round trip.

# Feature: frontend-backend-integration, Property 4: Diagram save/load round trip

For any valid DiagramState object and any session, saving the diagram via
the persistence layer and then loading it by the returned diagram ID shall
produce a DiagramState equivalent to the original.

**Validates: Requirements 3.1, 4.2, 9.5**
"""

import os
import shutil
import tempfile
import uuid

from hypothesis import given, settings, strategies as st

from app.persistence.tinydb_repo import TinyDBRepository

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

uuid4_st = st.builds(lambda: str(uuid.uuid4()))

viewport_st = st.fixed_dictionaries({
    "x": st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    "y": st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    "zoom": st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
})

element_st = st.fixed_dictionaries({
    "id": uuid4_st,
    "type": st.sampled_from(["lambda", "s3", "dynamodb", "api-gateway", "cloudwatch", "iam"]),
    "x": st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False),
    "y": st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False),
    "name": st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N", "Pd"))),
})

connector_st = st.fixed_dictionaries({
    "id": uuid4_st,
    "sourceId": uuid4_st,
    "targetId": uuid4_st,
    "type": st.sampled_from(["triggers", "reads_from", "writes_to", "logs_to", "uses"]),
})

environment_st = st.fixed_dictionaries({
    "name": st.sampled_from(["dev", "staging", "prod", "qa", "test"]),
    "variables": st.dictionaries(
        keys=st.from_regex(r"[a-z][a-z0-9_]{0,9}", fullmatch=True),
        values=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"))),
        min_size=0,
        max_size=3,
    ),
})

diagram_state_st = st.fixed_dictionaries({
    "version": st.integers(min_value=1, max_value=100),
    "projectName": st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N", "Pd", "Zs"))),
    "environments": st.lists(environment_st, min_size=0, max_size=4),
    "elements": st.lists(element_st, min_size=0, max_size=10),
    "connectors": st.lists(connector_st, min_size=0, max_size=8),
    "viewport": viewport_st,
})


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------

# Feature: frontend-backend-integration, Property 4: Diagram save/load round trip
class TestDiagramSaveLoadRoundTrip:
    """Property 4: Diagram save/load round trip.

    For any valid DiagramState object and any session, saving the diagram
    via the persistence layer and then loading it by the returned diagram ID
    shall produce a DiagramState equivalent to the original.
    """

    @given(session_id=uuid4_st, diagram_state=diagram_state_st)
    @settings(max_examples=100)
    def test_save_then_load_returns_equivalent_diagram_state(
        self, session_id: str, diagram_state: dict
    ) -> None:
        """Saving a diagram and loading it by the returned ID produces
        a diagram_state equivalent to the original."""
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "test_db.json")

        repo = TinyDBRepository(db_path=tmp_path)
        try:
            # Save the diagram
            diagram_id = repo.save_diagram(session_id, diagram_state)

            # diagram_id must be a non-empty string
            assert isinstance(diagram_id, str)
            assert len(diagram_id) > 0

            # Load the diagram by ID
            record = repo.get_diagram(diagram_id)

            # Must find the record
            assert record is not None, (
                f"get_diagram returned None for diagram_id={diagram_id}"
            )

            # The stored diagram_state must equal the original
            assert record.diagram_state == diagram_state, (
                f"Round-trip mismatch:\n"
                f"  original:  {diagram_state}\n"
                f"  loaded:    {record.diagram_state}"
            )

            # Verify ownership metadata
            assert record.session_id == session_id
            assert record.diagram_id == diagram_id
        finally:
            repo._db.close()
            shutil.rmtree(tmp_dir, ignore_errors=True)
