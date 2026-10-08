"""Tests for the connection catalog endpoint and typed connection configs."""

import pytest
from pydantic import ValidationError

from app.models.connection_configs.configs import (
    ApiGatewayRouteHandlerConfig,
    LambdaDynamoDBConfig,
    SqsLambdaConfig,
)
from app.models.input_models import ServiceType
from app.models.input_models.api_gateway_route import HTTP_METHODS
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
    def test_ecs_prometheus_collection_settings_are_served(self, connection_schemas):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "ecs" and item["target"] == "managed-prometheus"
        )
        assert entry["connection_type"] == "sends_metrics"
        fields = {item["key"]: item for item in entry["fields"]}
        assert fields["collection_interval_seconds"]["default"] == 60
        assert fields["collection_interval_seconds"]["validation"]["min"] == 10
        assert fields["application_metrics_port"]["default"] == 0
        assert fields["application_metrics_port"]["validation"]["max"] == 65535

    def test_eks_managed_collection_interval_is_served(self, connection_schemas):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "eks" and item["target"] == "managed-prometheus"
        )
        assert entry["connection_type"] == "sends_metrics"
        assert len(entry["fields"]) == 1
        field = entry["fields"][0]
        assert field["key"] == "scrape_interval_seconds" and field["type"] == "number"
        assert field["default"] == 60
        assert field["validation"]["min"] == 30 and field["validation"]["max"] == 3600

    def test_grafana_timestream_table_selector_is_served(self, connection_schemas):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "managed-grafana" and item["target"] == "timestream"
        )
        assert entry["connection_type"] == "queries"
        assert len(entry["fields"]) == 1
        field = entry["fields"][0]
        assert field["key"] == "table_name" and field["required"]
        assert field["validation"]["pattern"] == r"^[A-Za-z0-9_.-]{3,256}$"

    def test_grafana_cloudwatch_queries_are_served(self, connection_schemas):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "managed-grafana" and item["target"] == "cloudwatch"
        )
        assert entry["connection_type"] == "queries"
        assert entry["fields"] == []

    def test_grafana_prometheus_queries_are_served(self, connection_schemas):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "managed-grafana"
            and item["target"] == "managed-prometheus"
        )
        assert entry["connection_type"] == "queries"
        assert entry["fields"] == []

    def test_aws_config_sns_delivery_is_served(self, connection_schemas):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "aws-config" and item["target"] == "sns"
        )
        assert entry["connection_type"] == "notifies"
        assert entry["fields"] == []

    def test_cloudtrail_log_delivery_is_served(self, connection_schemas):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "cloudtrail" and item["target"] == "cloudwatch"
        )
        assert entry["connection_type"] == "logs_to"
        assert entry["fields"] == []

    def test_api_gateway_certificate_mapping_fields_are_served(
        self, connection_schemas
    ):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "certificate-manager"
            and item["target"] == "api-gateway"
        )
        assert entry["connection_type"] == "secures"
        fields = {item["key"]: item for item in entry["fields"]}
        assert fields["domain_name"]["required"] is True
        assert fields["stage_name"]["default"] == ""
        assert fields["api_mapping_key"]["default"] == ""

    def test_certificate_dns_validation_fields_are_served(self, connection_schemas):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "route53" and item["target"] == "certificate-manager"
        )
        assert entry["connection_type"] == "validates_certificate"
        fields = {item["key"]: item for item in entry["fields"]}
        assert fields["ttl"]["type"] == "number"
        assert fields["ttl"]["default"] == 60
        assert fields["ttl"]["validation"]["min"] == 1
        assert fields["ttl"]["validation"]["max"] == 2147483647

    def test_client_vpn_certificate_roles_are_served(self, connection_schemas):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "certificate-manager"
            and item["target"] == "client-vpn"
        )
        assert entry["connection_type"] == "secures"
        field = entry["fields"][0]
        assert field["key"] == "certificate_role"
        assert field["default"] == "server"
        assert [option["value"] for option in field["options"]] == [
            "server",
            "client_trust",
            "both",
        ]

    def test_private_certificate_key_choices_are_served(self, connection_schemas):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "private-certificate-authority"
            and item["target"] == "certificate-manager"
        )
        assert entry["connection_type"] == "issues_certificate"
        fields = {item["key"]: item for item in entry["fields"]}
        assert fields["key_algorithm"]["default"] == "AUTO"
        assert [item["value"] for item in fields["key_algorithm"]["options"]] == [
            "AUTO",
            "RSA_2048",
            "EC_prime256v1",
            "EC_secp384r1",
        ]

    def test_cognito_load_balancer_settings_are_served(self, connection_schemas):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "cognito" and item["target"] == "load-balancer"
        )
        assert entry["connection_type"] == "authenticates"
        fields = {field["key"]: field for field in entry["fields"]}
        assert fields["application_hostname"]["required"] is True
        assert fields["listener_port"]["default"] == 443
        assert fields["scopes"]["default"] == "openid"
        assert fields["session_timeout"]["validation"]["max"] == 604800
        assert [
            item["value"] for item in fields["on_unauthenticated_request"]["options"]
        ] == ["authenticate", "deny", "allow"]

    def test_cognito_api_gateway_route_settings_are_served(self, connection_schemas):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "cognito" and item["target"] == "api-gateway"
        )
        assert entry["connection_type"] == "authenticates"
        fields = {field["key"]: field for field in entry["fields"]}
        assert fields["path"]["required"] is True
        assert fields["method"]["default"] == "ANY"
        assert [option["value"] for option in fields["method"]["options"]] == list(
            HTTP_METHODS
        )
        assert fields["authorization_scopes"]["default"] is None

    def test_cognito_appsync_authentication_options_are_served(
        self, connection_schemas
    ):
        entry = next(
            item
            for item in connection_schemas["connections"]
            if item["source"] == "cognito" and item["target"] == "appsync"
        )
        assert entry["connection_type"] == "authenticates"
        fields = {field["key"]: field for field in entry["fields"]}
        assert fields["mode"]["default"] == "default"
        assert [option["value"] for option in fields["mode"]["options"]] == [
            "default",
            "additional",
        ]
        assert fields["restrict_to_client"]["default"] is True
        assert fields["default_action"]["visible_when"] == {
            "field": "mode",
            "equals": "default",
        }

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

    def test_linked_entry_fields_are_served_as_data(self, connection_schemas):
        """The editor must learn the routable HTTP methods from the API, not invent them."""
        entry = next(
            e
            for e in connection_schemas["connections"]
            if e["connection_type"] == "route_handler"
        )
        route = next(f for f in entry["fields"] if f["key"] == "route_path")
        methods = next(
            f for f in route["linked"]["entry_fields"] if f["key"] == "methods"
        )
        assert methods["type"] == "multiSelect"
        assert methods["exclusive_options"] == ["ANY"]
        assert [o["value"] for o in methods["options"]] == list(HTTP_METHODS)


@pytest.mark.parametrize("target", ["lambda", "sns", "sqs"])
def test_s3_notification_events_have_typed_defaults(connection_schemas, target):
    entry = next(
        item
        for item in connection_schemas["connections"]
        if item["source"] == "s3" and item["target"] == target
    )
    events = next(field for field in entry["fields"] if field["key"] == "events")
    assert events["default"] == ["s3:ObjectCreated:*"]
    assert events["type"] == "multiSelect"
    assert {option["value"] for option in events["options"]} == {
        "s3:ObjectCreated:*",
        "s3:ObjectRemoved:*",
        "s3:ObjectRestore:*",
    }


def test_grafana_athena_existing_glue_table_selectors_are_discoverable(
    connection_schemas,
):
    entry = next(
        item
        for item in connection_schemas["connections"]
        if item["source"] == "managed-grafana" and item["target"] == "athena"
    )
    assert entry["connection_type"] == "queries"
    fields = {field["key"]: field for field in entry["fields"]}
    assert set(fields) == {"database_name", "table_name"}
    for field in fields.values():
        assert field["required"] is True
        assert field["validation"]["pattern"] == r"^[a-z_][a-z0-9_]{0,254}$"


def test_grafana_redshift_existing_database_and_user_selectors_are_discoverable(
    connection_schemas,
):
    entry = next(
        item
        for item in connection_schemas["connections"]
        if item["source"] == "managed-grafana" and item["target"] == "redshift"
    )
    assert entry["connection_type"] == "queries"
    fields = {field["key"]: field for field in entry["fields"]}
    assert set(fields) == {"database_name", "database_user"}
    for field in fields.values():
        assert field["required"] is True
        assert field["validation"]["pattern"] == r"^[a-z][a-z0-9_]{0,63}$"


def test_grafana_xray_regional_query_connection_is_discoverable(connection_schemas):
    entry = next(
        item
        for item in connection_schemas["connections"]
        if item["source"] == "managed-grafana" and item["target"] == "x-ray"
    )
    assert entry["connection_type"] == "queries"
    assert "regional" in entry["label"]
    assert entry["fields"] == []


def test_lambda_xray_active_tracing_connection_is_discoverable(connection_schemas):
    entry = next(
        item
        for item in connection_schemas["connections"]
        if item["source"] == "lambda" and item["target"] == "x-ray"
    )
    assert entry["connection_type"] == "traces_to"
    assert "group membership" in entry["label"]
    assert entry["fields"] == []


def test_grafana_opensearch_default_index_and_time_field_are_discoverable(
    connection_schemas,
):
    entry = next(
        item
        for item in connection_schemas["connections"]
        if item["source"] == "managed-grafana" and item["target"] == "opensearch"
    )
    assert entry["connection_type"] == "queries"
    fields = {field["key"]: field for field in entry["fields"]}
    assert fields["index_name"]["required"] is True
    assert fields["index_name"]["label"] == "Default index name"
    assert (
        fields["index_name"]["validation"]["pattern"] == r"^[a-z0-9][a-z0-9_.-]{0,254}$"
    )
    assert fields["time_field"]["default"] == "@timestamp"
    assert fields["time_field"]["required"] is False
