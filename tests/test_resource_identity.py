"""Resource names are validated, and stable ids survive renames."""

import pytest
from pydantic import ValidationError

from app.models.input_models import (
    ArchitectureDescription,
    Connection,
    EnvironmentConfig,
    ResourceInstance,
    ServiceType,
)
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.input_models.dynamodb_config import DynamoDBConfig
from app.models.input_models.lambda_config import LambdaConfig
from app.services.ir_builder import IRBuilder


def _lambda(name: str, block_id: str | None = None) -> ResourceInstance:
    return ResourceInstance(
        id=block_id,
        name=name,
        service_type=ServiceType.LAMBDA,
        config=LambdaConfig(function_name=name, handler="h", runtime="python3.12"),
    )


def _arch(resources, connections=None) -> ArchitectureDescription:
    return ArchitectureDescription(
        project_name="proj",
        environments=[EnvironmentConfig(name="dev")],
        resources=resources,
        connections=connections or [],
    )


class TestNameValidation:
    def test_duplicate_names_are_rejected(self):
        with pytest.raises(ValidationError, match="Duplicate resource name"):
            _arch([_lambda("worker"), _lambda("worker")])

    def test_name_with_spaces_is_rejected(self):
        with pytest.raises(ValidationError, match="Invalid resource name"):
            _arch([_lambda("my worker")])

    def test_name_starting_with_a_digit_is_rejected(self):
        with pytest.raises(ValidationError, match="Invalid resource name"):
            _arch([_lambda("1worker")])

    @pytest.mark.parametrize("name", ["worker", "my-worker", "my_worker", "_worker"])
    def test_valid_names_are_accepted(self, name):
        assert _arch([_lambda(name)]).resources[0].name == name


class TestEndpointsResolveById:
    def test_stale_name_still_resolves_through_the_id(self):
        table = ResourceInstance(
            id="tbl-1",
            name="users",
            service_type=ServiceType.DYNAMODB,
            config=DynamoDBConfig(table_name="users", hash_key="id", hash_key_type="S"),
        )
        arch = _arch(
            [_lambda("renamed-worker", block_id="block-1"), table],
            [
                Connection(
                    source="renamed-worker",
                    target="users",
                    source_id="block-1",
                    target_id="tbl-1",
                    connection_type="accesses",
                )
            ],
        )
        # The client held a stale name; only the id is current
        arch.connections[0].source = "old-name"

        ir = IRBuilder().build(arch)
        assert ir.connections[0].source_name == "renamed-worker"

    def test_unknown_name_without_an_id_still_errors(self):
        from app.exceptions import ResourceNotFoundError

        arch = _arch([_lambda("worker")])
        arch.connections = [
            Connection(source="ghost", target="worker", connection_type="triggers")
        ]
        with pytest.raises(ResourceNotFoundError):
            IRBuilder().build(arch)


class TestRenameDoesNotOrphanRoutes:
    """The bug this phase exists to fix."""

    def _gateway(self, integration_name: str, integration_id: str | None):
        route: dict = {"methods": ["GET"], "path": "/users"}
        route["integration_name"] = integration_name
        if integration_id:
            route["integration_id"] = integration_id
        return ResourceInstance(
            id="gw-1",
            name="public-api",
            service_type=ServiceType.API_GATEWAY,
            config=ApiGatewayConfig(
                api_name="public-api", protocol_type="HTTP", routes=[route]
            ),
        )

    def _derive(self, gateway, function):
        arch = _arch(
            [gateway, function],
            [
                Connection(
                    source="public-api",
                    target=function.name,
                    source_id="gw-1",
                    target_id=function.id,
                    connection_type="route_handler",
                )
            ],
        )
        return IRBuilder().build(arch).connections[0].connection_config["routes"]

    def test_routes_survive_a_rename_when_the_id_matches(self):
        gateway = self._gateway(integration_name="old-name", integration_id="fn-1")
        function = _lambda("new-name", block_id="fn-1")
        assert len(self._derive(gateway, function)) == 1

    def test_routes_are_dropped_when_the_id_points_elsewhere(self):
        gateway = self._gateway(integration_name="new-name", integration_id="other")
        function = _lambda("new-name", block_id="fn-1")
        assert self._derive(gateway, function) == []

    def test_name_matching_still_works_without_ids(self):
        gateway = self._gateway(integration_name="worker", integration_id=None)
        function = _lambda("worker")
        assert len(self._derive(gateway, function)) == 1
