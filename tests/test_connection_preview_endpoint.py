"""Tests for the connection preview endpoint and the handler validation hook."""

import importlib

import pytest
from fastapi.testclient import TestClient

from app.services.connection_handlers.registry import CONNECTION_SPECS


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A test client backed by an isolated repository."""
    from app.persistence.tinydb_repo import TinyDBRepository

    temp_repo = TinyDBRepository(db_path=str(tmp_path / "test_db.json"))
    monkeypatch.setattr("app.persistence.factory.get_repository", lambda: temp_repo)

    import app.main as main_mod

    importlib.reload(main_mod)

    from app.routers.diagrams import get_repo

    main_mod.app.dependency_overrides[get_repo] = lambda: temp_repo

    with TestClient(main_mod.app) as test_client:
        yield test_client
    temp_repo._db.close()


def _architecture(resources, connections):
    return {
        "project_name": "preview-test",
        "environments": [{"name": "dev", "variables": {}}],
        "resources": resources,
        "connections": connections,
    }


def _preview(client, payload):
    response = client.post("/api/connections/preview", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["previews"]


class TestEmptyConnectionsStillPreview:
    """The five connections with no fields are exactly the ones a panel must inform about."""

    def test_lambda_to_cloudwatch_reports_its_log_group_and_grant(self, client):
        previews = _preview(
            client,
            _architecture(
                [
                    {
                        "name": "worker",
                        "service_type": "lambda",
                        "config": {
                            "function_name": "worker",
                            "handler": "index.handler",
                            "runtime": "python3.12",
                        },
                    },
                    {"name": "logs", "service_type": "cloudwatch", "config": {}},
                ],
                [
                    {
                        "source": "worker",
                        "target": "logs",
                        "connection_type": "logs_to",
                    }
                ],
            ),
        )

        assert len(previews) == 1
        preview = previews[0]
        assert preview["label"] == "Lambda → CloudWatch"
        assert [r["resource_type"] for r in preview["resources"]] == [
            "aws_cloudwatch_log_group"
        ]
        assert preview["iam"][0]["role_owner"] == "worker"
        assert preview["iam"][0]["effect"] == "Allow"
        assert preview["iam"][0]["actions"]

    def test_sns_to_sqs_reports_both_emitted_resources(self, client):
        previews = _preview(
            client,
            _architecture(
                [
                    {"name": "events", "service_type": "sns", "config": {}},
                    {"name": "inbox", "service_type": "sqs", "config": {}},
                ],
                [
                    {
                        "source": "events",
                        "target": "inbox",
                        "connection_type": "delivers_to",
                    }
                ],
            ),
        )

        types = {r["resource_type"] for r in previews[0]["resources"]}
        assert types == {"aws_sns_topic_subscription", "aws_sqs_queue_policy"}
        assert all(r["module"] == "inbox" for r in previews[0]["resources"])


class TestIncompleteConnectionsAreReported:
    def _apigw_architecture(self, routes):
        return _architecture(
            [
                {
                    "name": "gateway",
                    "service_type": "api-gateway",
                    "config": {
                        "api_name": "gateway",
                        "protocol_type": "HTTP",
                        "routes": routes,
                    },
                },
                {
                    "name": "handler",
                    "service_type": "lambda",
                    "config": {
                        "function_name": "handler",
                        "handler": "index.handler",
                        "runtime": "python3.12",
                    },
                },
            ],
            [
                {
                    "source": "gateway",
                    "target": "handler",
                    "connection_type": "route_handler",
                }
            ],
        )

    def test_route_handler_without_a_matching_route_warns(self, client):
        previews = _preview(client, self._apigw_architecture([]))

        assert len(previews[0]["issues"]) == 1
        issue = previews[0]["issues"][0]
        assert issue["severity"] == "warning"
        assert "gateway" in issue["message"] and "handler" in issue["message"]

    def test_route_handler_with_a_matching_route_is_clean(self, client):
        previews = _preview(
            client,
            self._apigw_architecture(
                [
                    {
                        "path": "/items",
                        "methods": ["GET"],
                        "integration_name": "handler",
                    }
                ]
            ),
        )

        assert previews[0]["issues"] == []
        route_types = [r["resource_type"] for r in previews[0]["resources"]]
        assert "aws_apigatewayv2_route" in route_types


class TestPreviewIdentity:
    def test_stable_ids_are_echoed_back(self, client):
        previews = _preview(
            client,
            _architecture(
                [
                    {
                        "id": "block-1",
                        "name": "worker",
                        "service_type": "lambda",
                        "config": {
                            "function_name": "worker",
                            "handler": "index.handler",
                            "runtime": "python3.12",
                        },
                    },
                    {
                        "id": "block-2",
                        "name": "table",
                        "service_type": "dynamodb",
                        "config": {
                            "table_name": "table",
                            "hash_key": "id",
                            "hash_key_type": "S",
                        },
                    },
                ],
                [
                    {
                        "source": "worker",
                        "target": "table",
                        "source_id": "block-1",
                        "target_id": "block-2",
                        "connection_type": "accesses",
                    }
                ],
            ),
        )

        assert previews[0]["source_id"] == "block-1"
        assert previews[0]["target_id"] == "block-2"

    def test_every_handler_answers_the_validation_hook(self):
        """The preview calls validate on whatever spec resolves, so all must implement it."""
        for spec in CONNECTION_SPECS:
            assert callable(spec.handler.validate)
