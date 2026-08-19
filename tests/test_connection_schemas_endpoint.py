"""Tests for the connection catalog endpoint and typed connection configs."""

import pytest
from pydantic import ValidationError

from app.models.connection_configs.configs import (
    ApiGatewayRouteHandlerConfig,
    LambdaDynamoDBConfig,
    SqsLambdaConfig,
)
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import (
    COMPATIBLE_CONNECTIONS,
    CONNECTION_REGISTRY,
    CONNECTION_SPECS,
    resolve_spec,
)


@pytest.fixture()
def connection_schemas(tmp_path, monkeypatch):
    """Fetch the catalog from the real app on an isolated repository."""
    from fastapi.testclient import TestClient

    from app.persistence.tinydb_repo import TinyDBRepository

    temp_repo = TinyDBRepository(db_path=str(tmp_path / "test_db.json"))
    monkeypatch.setattr("app.persistence.factory.get_repository", lambda: temp_repo)

    import importlib

    import app.main as main_mod

    importlib.reload(main_mod)

    # diagrams.py binds get_repository at its own import time, which can predate the patch
    from app.routers.diagrams import get_repo

    main_mod.app.dependency_overrides[get_repo] = lambda: temp_repo

    with TestClient(main_mod.app) as client:
        response = client.get("/api/connection-schemas")
        assert response.status_code == 200
        yield response.json()
    temp_repo._db.close()


class TestRegistryIsSingleSourceOfTruth:
    def test_compatible_pairs_derive_from_specs(self):
        assert {
            (s.source, s.target) for s in CONNECTION_SPECS
        } == COMPATIBLE_CONNECTIONS

    def test_every_spec_is_reachable_by_key(self):
        for spec in CONNECTION_SPECS:
            assert CONNECTION_REGISTRY[spec.key] is spec

    def test_each_pair_has_exactly_one_default(self):
        for source, target in COMPATIBLE_CONNECTIONS:
            defaults = [
                s
                for s in CONNECTION_SPECS
                if s.source is source and s.target is target and s.is_default
            ]
            assert len(defaults) == 1


class TestSpecResolution:
    def test_exact_connection_type_wins(self):
        spec = resolve_spec(
            ServiceType.API_GATEWAY, ServiceType.LAMBDA, "authorizer", {}
        )
        assert spec.connection_type == "authorizer"

    def test_legacy_connection_role_is_honoured(self):
        spec = resolve_spec(
            ServiceType.API_GATEWAY,
            ServiceType.LAMBDA,
            "triggers",
            {"connection_role": "authorizer"},
        )
        assert spec.connection_type == "authorizer"

    def test_unknown_type_falls_back_to_default(self):
        spec = resolve_spec(ServiceType.API_GATEWAY, ServiceType.LAMBDA, "triggers", {})
        assert spec.connection_type == "route_handler"

    def test_single_spec_pair_ignores_connection_type(self):
        spec = resolve_spec(ServiceType.LAMBDA, ServiceType.S3, "anything", {})
        assert spec.connection_type == "accesses"

    def test_unsupported_pair_resolves_to_none(self):
        assert resolve_spec(ServiceType.S3, ServiceType.EC2, "triggers", {}) is None


class TestTypedConfigValidation:
    def test_unknown_key_is_rejected(self):
        with pytest.raises(ValidationError):
            LambdaDynamoDBConfig(acces_pattern="read")

    def test_out_of_range_value_is_rejected(self):
        with pytest.raises(ValidationError):
            SqsLambdaConfig(batch_size=0)

    def test_defaults_are_applied(self):
        assert SqsLambdaConfig().batch_size == 10
        assert LambdaDynamoDBConfig().access_pattern == "full"

    def test_route_handler_exposes_its_fields(self):
        keys = {f.key for f in ApiGatewayRouteHandlerConfig.get_field_schema()}
        assert {"route_path", "payload_format_version", "integration_type"} <= keys

    def test_derived_routes_are_not_user_configurable(self):
        keys = {f.key for f in ApiGatewayRouteHandlerConfig.get_field_schema()}
        assert "routes" not in keys


class TestConnectionSchemasEndpoint:
    def test_returns_every_spec(self, connection_schemas):
        assert len(connection_schemas["connections"]) == len(CONNECTION_SPECS)

    def test_entries_carry_pair_and_type(self, connection_schemas):
        entry = next(
            e
            for e in connection_schemas["connections"]
            if e["connection_type"] == "authorizer"
        )
        assert entry["source"] == "api-gateway"
        assert entry["target"] == "lambda"
        assert entry["is_default"] is False

    def test_field_validation_is_served_as_data(self, connection_schemas):
        entry = next(
            e
            for e in connection_schemas["connections"]
            if e["source"] == "sqs" and e["target"] == "lambda"
        )
        batch = next(f for f in entry["fields"] if f["key"] == "batch_size")
        assert batch["type"] == "number"
        assert batch["default"] == 10
        assert batch["validation"]["min"] == 1
        assert batch["validation"]["max"] == 10000
