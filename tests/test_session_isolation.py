"""Property-based test for session isolation on all diagram operations.

# Feature: frontend-backend-integration, Property 6: Session isolation on all diagram operations

For any diagram owned by session A and any distinct session B, list_diagrams
for session B shall return empty (the diagram does not leak across sessions),
and list_diagrams for session A shall include the diagram.

The isolation enforcement for read/update/delete of individual diagrams happens
at the router level (HTTP 403), not the repository level — so the repository's
get_diagram will still return the record regardless of caller session. This test
focuses on the list_diagrams boundary.

**Validates: Requirements 3.3, 4.3, 5.2**
"""

import os
import shutil
import tempfile
import uuid

from hypothesis import given, settings, assume, strategies as st

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

# Feature: frontend-backend-integration, Property 6: Session isolation on all diagram operations
class TestSessionIsolation:
    """Property 6: Session isolation on all diagram operations.

    For any diagram owned by session A and any distinct session B,
    list_diagrams for session B returns empty and list_diagrams for
    session A includes the diagram.

    **Validates: Requirements 3.3, 4.3, 5.2**
    """

    @given(
        session_a=uuid4_st,
        session_b=uuid4_st,
        diagram_state=diagram_state_st,
    )
    @settings(max_examples=100)
    def test_session_isolation_on_list_diagrams(
        self, session_a: str, session_b: str, diagram_state: dict
    ) -> None:
        """Diagrams saved by session A do not appear in session B's
        list_diagrams, and do appear in session A's list_diagrams."""
        assume(session_a != session_b)

        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "test_db.json")

        repo = TinyDBRepository(db_path=tmp_path)
        try:
            # Save a diagram under session A
            diagram_id = repo.save_diagram(session_a, diagram_state)
            assert isinstance(diagram_id, str) and len(diagram_id) > 0

            # list_diagrams for session B should return empty
            summaries_b = repo.list_diagrams(session_b)
            assert summaries_b == [], (
                f"Session B should see no diagrams but got: {summaries_b}"
            )

            # list_diagrams for session A should contain exactly the saved diagram
            summaries_a = repo.list_diagrams(session_a)
            assert len(summaries_a) == 1, (
                f"Session A should see exactly 1 diagram but got {len(summaries_a)}"
            )
            assert summaries_a[0].diagram_id == diagram_id
            assert summaries_a[0].project_name == diagram_state.get("projectName", "")
        finally:
            repo._db.close()
            shutil.rmtree(tmp_dir, ignore_errors=True)
