"""Unit tests for the GET /api/variable-schemas endpoint.

Validates:
- Endpoint returns 200 with valid JSON (Requirement 7.4)
- Response contains all 5 service types as keys (Requirement 9.1)
- Each service type maps to a list of schema entries
- Each entry has required fields: name, type, description
- Entries with options have the correct {value, label} structure
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Build a TestClient from the real app, using a temp TinyDB file."""
    db_path = str(tmp_path / "test_db.json")

    from app.persistence.tinydb_repo import TinyDBRepository

    temp_repo = TinyDBRepository(db_path=db_path)
    monkeypatch.setattr("app.persistence.factory.get_repository", lambda: temp_repo)

    import importlib

    import app.main as main_mod

    importlib.reload(main_mod)

    # See tests/test_cors_and_wiring.py for why this override is also needed:
    # app.routers.diagrams binds get_repository at its own import time, which
    # can predate this patch depending on test collection order.
    from app.routers.diagrams import get_repo

    main_mod.app.dependency_overrides[get_repo] = lambda: temp_repo

    yield TestClient(main_mod.app)
    temp_repo._db.close()


EXPECTED_SERVICE_TYPES = {
    "lambda",
    "s3",
    "dynamodb",
    "api-gateway",
    "cloudwatch",
    "sns",
    "sqs",
    "ec2",
    "ecs",
    "eks",
    "elastic-beanstalk",
    "app-runner",
    "batch",
    "ec2-image-builder",
    "lightsail",
    "ecr",
    # Analytics
    "athena",
    "cloudsearch",
    "emr",
    "glue",
    "kinesis",
    "kinesis-firehose",
    "msk",
    "opensearch",
    "redshift",
    # Business Applications
    "connect",
    "ses",
    "pinpoint",
    # Database
    "aurora",
    "documentdb",
    "elasticache",
    "neptune",
    "rds",
    "timestream",
    # Developer Tools
    "codebuild",
    "codecommit",
    "codedeploy",
    "codepipeline",
    # End User Computing
    "appstream",
    # Front End Web Mobile
    "amplify",
    # Games
    "gamelift",
    # Machine Learning
    "bedrock",
    "sagemaker",
    "amazon-q",
    "bedrock-agent",
    "bedrock-guardrail",
    "bedrock-knowledge-base",
    "bedrock-agentcore",
}


class TestVariableSchemasEndpoint:
    """Tests for GET /api/variable-schemas."""

    def test_returns_200(self, client):
        """Endpoint returns HTTP 200."""
        resp = client.get("/api/variable-schemas")
        assert resp.status_code == 200

    def test_contains_all_service_types(self, client):
        """Response JSON contains all 5 service types as top-level keys."""
        data = client.get("/api/variable-schemas").json()
        assert set(data.keys()) == EXPECTED_SERVICE_TYPES

    def test_each_service_type_has_list_of_entries(self, client):
        """Each service type maps to a non-empty list."""
        data = client.get("/api/variable-schemas").json()
        for stype, entries in data.items():
            assert isinstance(entries, list), f"{stype} value is not a list"
            assert len(entries) > 0, f"{stype} has no schema entries"

    def test_entries_have_required_fields(self, client):
        """Every entry has name, type, and description fields."""
        data = client.get("/api/variable-schemas").json()
        for stype, entries in data.items():
            for entry in entries:
                assert "name" in entry, f"{stype}: entry missing 'name'"
                assert "type" in entry, f"{stype}: entry missing 'type'"
                assert "description" in entry, f"{stype}: entry missing 'description'"
                assert isinstance(entry["name"], str)
                assert isinstance(entry["type"], str)
                assert isinstance(entry["description"], str)

    def test_options_have_value_and_label(self, client):
        """Entries with options have the correct {value, label} structure."""
        data = client.get("/api/variable-schemas").json()
        found_options = False
        for stype, entries in data.items():
            for entry in entries:
                if entry.get("options") is not None:
                    found_options = True
                    for opt in entry["options"]:
                        assert "value" in opt, (
                            f"{stype}/{entry['name']}: option missing 'value'"
                        )
                        assert "label" in opt, (
                            f"{stype}/{entry['name']}: option missing 'label'"
                        )
                        assert isinstance(opt["label"], str)
        assert found_options, "No entries with options found — test is vacuous"
