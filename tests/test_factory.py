"""Unit tests for the repository factory."""


import pytest

from app.persistence.factory import get_repository
from app.persistence.tinydb_repo import TinyDBRepository


class TestGetRepository:
    """Verify get_repository selects the correct backend."""

    def test_defaults_to_tinydb(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PERSISTENCE_BACKEND", raising=False)
        monkeypatch.setenv("TINYDB_PATH", str(tmp_path / "db.json"))
        # Patch TinyDBRepository to use tmp path
        monkeypatch.setattr(
            "app.persistence.tinydb_repo._DEFAULT_DB_PATH",
            str(tmp_path / "db.json"),
        )
        repo = get_repository()
        assert isinstance(repo, TinyDBRepository)

    def test_explicit_tinydb(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PERSISTENCE_BACKEND", "tinydb")
        monkeypatch.setattr(
            "app.persistence.tinydb_repo._DEFAULT_DB_PATH",
            str(tmp_path / "db.json"),
        )
        repo = get_repository()
        assert isinstance(repo, TinyDBRepository)

    def test_case_insensitive(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PERSISTENCE_BACKEND", "TinyDB")
        monkeypatch.setattr(
            "app.persistence.tinydb_repo._DEFAULT_DB_PATH",
            str(tmp_path / "db.json"),
        )
        repo = get_repository()
        assert isinstance(repo, TinyDBRepository)

    def test_dynamodb_selected(self, monkeypatch):
        monkeypatch.setenv("PERSISTENCE_BACKEND", "dynamodb")
        # DynamoDBRepository needs boto3 and real/mock tables — just verify
        # the import path is reached by catching the expected boto3 call.
        from unittest.mock import MagicMock, patch

        with patch("boto3.resource") as mock_resource:
            mock_table = MagicMock()
            mock_resource.return_value.Table.return_value = mock_table
            from app.persistence.dynamodb_repo import DynamoDBRepository

            repo = get_repository()
            assert isinstance(repo, DynamoDBRepository)

    def test_unknown_backend_raises(self, monkeypatch):
        monkeypatch.setenv("PERSISTENCE_BACKEND", "postgres")
        with pytest.raises(ValueError, match="Unknown PERSISTENCE_BACKEND"):
            get_repository()
