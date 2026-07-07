"""Property-based tests for session management.

Tests the persistence layer's session creation and resolution behaviour
using Hypothesis and a temporary TinyDB file.
"""

import os
import re
import tempfile
import uuid

from hypothesis import given, settings
from hypothesis import strategies as st

from app.persistence.models import UserRecord
from app.persistence.tinydb_repo import TinyDBRepository

# Regex patterns
UUID_V4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
ISO_8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+\d{2}:\d{2}|Z)?$",
)

# Strategy: generate random UUID v4 session IDs
uuid4_session_id_st = st.builds(lambda: str(uuid.uuid4()))


# Feature: frontend-backend-integration, Property 1: Session creation produces a valid UserRecord
# **Validates: Requirements 1.1, 2.1**
class TestSessionCreationProducesValidUserRecord:
    """Property 1: Session creation produces a valid UserRecord.

    For any HTTP request without a valid session cookie, the Session Manager
    shall create a new UserRecord containing a UUID v4 session identifier,
    an ISO 8601 creation timestamp, and an ISO 8601 last-active timestamp.
    """

    @given(session_id=uuid4_session_id_st)
    @settings(max_examples=100)
    def test_create_user_returns_valid_user_record(self, session_id: str) -> None:
        """Creating a user with a UUID v4 session ID produces a UserRecord
        with matching session_id and valid ISO 8601 timestamps."""
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "test_db.json")

        repo = TinyDBRepository(db_path=tmp_path)
        try:
            record = repo.create_user(session_id)

            # Must return a UserRecord instance
            assert isinstance(record, UserRecord)

            # session_id must match the input
            assert record.session_id == session_id

            # session_id must be a valid UUID v4
            assert UUID_V4_RE.match(record.session_id), (
                f"session_id is not a valid UUID v4: {record.session_id}"
            )

            # created_at must be a valid ISO 8601 timestamp
            assert ISO_8601_RE.match(record.created_at), (
                f"created_at is not valid ISO 8601: {record.created_at}"
            )

            # last_active must be a valid ISO 8601 timestamp
            assert ISO_8601_RE.match(record.last_active), (
                f"last_active is not valid ISO 8601: {record.last_active}"
            )
        finally:
            repo._db.close()
            import shutil

            shutil.rmtree(tmp_dir, ignore_errors=True)


# Feature: frontend-backend-integration, Property 2: Existing session resolution is idempotent
# **Validates: Requirements 1.2**
class TestExistingSessionResolutionIsIdempotent:
    """Property 2: Existing session resolution is idempotent.

    For any existing session in the persistence layer, calling get_user with
    that session's ID shall resolve to the same UserRecord without creating
    any additional UserRecords — the total user count shall remain unchanged.
    """

    @given(session_id=uuid4_session_id_st)
    @settings(max_examples=100)
    def test_get_user_resolves_same_record_without_creating_new(
        self, session_id: str
    ) -> None:
        """Calling get_user multiple times on an existing session returns the
        same UserRecord each time and does not increase the total user count."""
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "test_db.json")

        repo = TinyDBRepository(db_path=tmp_path)
        try:
            # Create the user first
            original = repo.create_user(session_id)
            count_after_create = len(repo._users.all())

            # Resolve the session multiple times
            resolved_1 = repo.get_user(session_id)
            resolved_2 = repo.get_user(session_id)
            resolved_3 = repo.get_user(session_id)

            count_after_gets = len(repo._users.all())

            # Each resolution must return a UserRecord (not None)
            assert resolved_1 is not None
            assert resolved_2 is not None
            assert resolved_3 is not None

            # Resolved records must match the original
            assert resolved_1.session_id == original.session_id
            assert resolved_1.created_at == original.created_at
            assert resolved_1.last_active == original.last_active

            assert resolved_2.session_id == original.session_id
            assert resolved_2.created_at == original.created_at
            assert resolved_2.last_active == original.last_active

            assert resolved_3.session_id == original.session_id
            assert resolved_3.created_at == original.created_at
            assert resolved_3.last_active == original.last_active

            # Total user count must not have changed
            assert count_after_gets == count_after_create
        finally:
            repo._db.close()
            import shutil

            shutil.rmtree(tmp_dir, ignore_errors=True)


# Feature: frontend-backend-integration, Property 3: Session touch updates last-active timestamp
# **Validates: Requirements 2.2**
class TestSessionTouchUpdatesLastActiveTimestamp:
    """Property 3: Session touch updates last-active timestamp.

    For any existing session, processing a request for that session shall
    result in the UserRecord's last-active timestamp being greater than or
    equal to its previous value.
    """

    @given(session_id=uuid4_session_id_st)
    @settings(max_examples=100)
    def test_update_user_last_active_increases_timestamp(self, session_id: str) -> None:
        """After calling update_user_last_active, the last_active timestamp
        on the UserRecord must be >= the previous value."""
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "test_db.json")

        repo = TinyDBRepository(db_path=tmp_path)
        try:
            # Create a user and record the initial last_active
            record = repo.create_user(session_id)
            old_last_active = record.last_active

            # Touch the session (simulates processing a request)
            repo.update_user_last_active(session_id)

            # Retrieve the updated record
            updated = repo.get_user(session_id)
            assert updated is not None

            # The new last_active must be >= the old one (ISO 8601 strings
            # are lexicographically comparable for UTC timestamps)
            assert updated.last_active >= old_last_active, (
                f"last_active went backwards: {updated.last_active} < {old_last_active}"
            )
        finally:
            repo._db.close()
            import shutil

            shutil.rmtree(tmp_dir, ignore_errors=True)
