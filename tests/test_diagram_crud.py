"""Property-based tests for diagram CRUD operations.

# Feature: frontend-backend-integration, Property 5: Diagram update then load returns updated state

**Validates: Requirements 3.2**
"""

import os
import shutil
import tempfile
import uuid

from hypothesis import given, settings, assume, strategies as st

from app.persistence.tinydb_repo import TinyDBRepository

# ---------------------------------------------------------------------------
# Strategies (reused from test_persistence_roundtrip.py)
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

# Feature: frontend-backend-integration, Property 5: Diagram update then load returns updated state
class TestDiagramUpdateThenLoad:
    """Property 5: Diagram update then load returns updated state.

    For any existing diagram owned by a session and any new valid DiagramState,
    updating the diagram and then loading it shall return the new DiagramState,
    not the original.

    **Validates: Requirements 3.2**
    """

    @given(
        session_id=uuid4_st,
        original_state=diagram_state_st,
        updated_state=diagram_state_st,
    )
    @settings(max_examples=100)
    def test_update_then_load_returns_updated_state(
        self, session_id: str, original_state: dict, updated_state: dict
    ) -> None:
        """Saving a diagram, updating it with a new state, then loading it
        returns the updated state, not the original."""
        assume(original_state != updated_state)

        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "test_db.json")

        repo = TinyDBRepository(db_path=tmp_path)
        try:
            # Save the original diagram
            diagram_id = repo.save_diagram(session_id, original_state)
            assert isinstance(diagram_id, str) and len(diagram_id) > 0

            # Update with the new state
            success = repo.update_diagram(diagram_id, updated_state)
            assert success is True, (
                f"update_diagram returned False for diagram_id={diagram_id}"
            )

            # Load and verify it matches the updated state
            record = repo.get_diagram(diagram_id)
            assert record is not None, (
                f"get_diagram returned None for diagram_id={diagram_id}"
            )

            assert record.diagram_state == updated_state, (
                f"After update, loaded state does not match updated state:\n"
                f"  original:  {original_state}\n"
                f"  updated:   {updated_state}\n"
                f"  loaded:    {record.diagram_state}"
            )

            # Verify it is NOT the original
            assert record.diagram_state != original_state, (
                f"After update, loaded state still matches the original:\n"
                f"  original:  {original_state}\n"
                f"  loaded:    {record.diagram_state}"
            )

            # Verify ownership metadata is preserved
            assert record.session_id == session_id
            assert record.diagram_id == diagram_id
        finally:
            repo._db.close()
            shutil.rmtree(tmp_dir, ignore_errors=True)


# Feature: frontend-backend-integration, Property 8: List diagrams returns correct summaries for session
class TestListDiagramsReturnsCorrectSummaries:
    """Property 8: List diagrams returns correct summaries for session.

    For any session that has saved N diagrams, a GET to /api/diagrams shall
    return exactly N diagram summaries, each containing a diagram_id,
    project_name, and updated_at field, and the set of diagram IDs shall match
    exactly the IDs returned when those diagrams were saved.

    **Validates: Requirements 4.1**
    """

    @given(
        session_id=uuid4_st,
        diagram_states=st.lists(diagram_state_st, min_size=1, max_size=5),
    )
    @settings(max_examples=100)
    def test_list_diagrams_returns_correct_summaries(
        self, session_id: str, diagram_states: list[dict]
    ) -> None:
        """Saving N diagrams under a session and listing them returns exactly
        N summaries whose IDs match the saved diagram IDs."""
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "test_db.json")

        repo = TinyDBRepository(db_path=tmp_path)
        try:
            # Save all diagrams and collect their IDs
            saved_ids: list[str] = []
            for state in diagram_states:
                diagram_id = repo.save_diagram(session_id, state)
                assert isinstance(diagram_id, str) and len(diagram_id) > 0
                saved_ids.append(diagram_id)

            # List diagrams for the session
            summaries = repo.list_diagrams(session_id)

            # Verify count matches
            assert len(summaries) == len(diagram_states), (
                f"Expected {len(diagram_states)} summaries, got {len(summaries)}"
            )

            # Verify each summary has the required fields
            for summary in summaries:
                assert hasattr(summary, "diagram_id") and isinstance(summary.diagram_id, str)
                assert hasattr(summary, "project_name") and isinstance(summary.project_name, str)
                assert hasattr(summary, "updated_at") and isinstance(summary.updated_at, str)

            # Verify the set of diagram IDs matches exactly
            summary_ids = {s.diagram_id for s in summaries}
            assert summary_ids == set(saved_ids), (
                f"Summary IDs {summary_ids} do not match saved IDs {set(saved_ids)}"
            )
        finally:
            repo._db.close()
            shutil.rmtree(tmp_dir, ignore_errors=True)


# Feature: frontend-backend-integration, Property 9: Delete removes diagram from persistence
class TestDeleteRemovesDiagramFromPersistence:
    """Property 9: Delete removes diagram from persistence.

    For any diagram owned by a session, deleting it shall return True, and
    subsequently attempting to load that diagram shall return None.

    **Validates: Requirements 5.1**
    """

    @given(
        session_id=uuid4_st,
        diagram_state=diagram_state_st,
    )
    @settings(max_examples=100)
    def test_delete_removes_diagram_from_persistence(
        self, session_id: str, diagram_state: dict
    ) -> None:
        """Saving a diagram, deleting it, then verifying get_diagram returns
        None and list_diagrams returns an empty list."""
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "test_db.json")

        repo = TinyDBRepository(db_path=tmp_path)
        try:
            # Save the diagram
            diagram_id = repo.save_diagram(session_id, diagram_state)
            assert isinstance(diagram_id, str) and len(diagram_id) > 0

            # Delete the diagram
            deleted = repo.delete_diagram(diagram_id)
            assert deleted is True, (
                f"delete_diagram returned False for diagram_id={diagram_id}"
            )

            # Verify get_diagram returns None
            record = repo.get_diagram(diagram_id)
            assert record is None, (
                f"get_diagram should return None after deletion, got {record}"
            )

            # Verify list_diagrams returns empty
            summaries = repo.list_diagrams(session_id)
            assert summaries == [], (
                f"list_diagrams should return empty list after deletion, "
                f"got {len(summaries)} summaries"
            )
        finally:
            repo._db.close()
            shutil.rmtree(tmp_dir, ignore_errors=True)
