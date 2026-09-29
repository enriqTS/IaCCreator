"""AppSync EventBridge connections publish scoped single-event mutations."""

import json
from copy import deepcopy

import hcl2
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.appsync_eventbridge import AppSyncEventBridgeConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from tests.generator_helpers import connection_architecture
from tests.test_appsync_dynamodb_connections import (
    architecture as dynamodb_architecture,
)
from tests.test_appsync_lambda_connections import architecture as lambda_architecture
from tests.test_appsync_opensearch_connections import (
    architecture as opensearch_architecture,
)
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.APPSYNC, ServiceType.EVENTBRIDGE, None, {})
    )


def file_with(tree, needle):
    return next(value for path, value in tree.items() if needle in path)


def resolver_code(tree, needle="/eventbridge_resolver_"):
    resolver = file_with(tree, needle)
    resource = hcl2.loads(resolver)["resource"][0]['"aws_appsync_resolver"']
    return json.loads(next(iter(resource.values()))["code"])


@pytest.mark.parametrize("custom_bus", [False, True])
def test_bus_scoped_publisher_and_single_event_resolver(custom_bus):
    payload = architecture()
    if custom_bus:
        payload["resources"][1]["config"]["bus_name"] = "application-bus"
    tree = generate(payload)
    source = file_with(tree, "/eventbridge_datasource_target-resource.tf")
    resolver = file_with(tree, "/eventbridge_resolver_Mutation_probe_")
    code = resolver_code(tree)
    main = tree["connection-check/environments/dev/main.tf"]
    bus = file_with(tree, "/eventbridge/target-resource/eventbridge.tf")
    outputs = file_with(tree, "/eventbridge/target-resource/outputs.tf")
    assert 'Service = "appsync.amazonaws.com"' in source
    assert "aws_appsync_graphql_api.source-resource.arn" in source
    assert '"events:PutEvents"' in source
    assert "var.appsync_target-resource_event_bus_arn" in source
    assert 'type = "AMAZON_EVENTBRIDGE"' in source
    assert "event_bridge_config" in source
    assert "aws_iam_role_policy.eventbridge_target-resource_publish" in source
    assert "module.target-resource.event_bus_arn" in main
    if custom_bus:
        assert "aws_cloudwatch_event_bus.target-resource_bus.arn" in outputs
    else:
        assert "data.aws_cloudwatch_event_bus.default.arn" in outputs
        assert 'name = "default"' in bus
    assert "operation: 'PutEvents'" in code
    assert 'source: "com.example.app"' in code
    assert 'detailType: "ApplicationEvent"' in code
    assert 'detail: ctx.args["input"]' in code
    assert "FailedEntryCount > 0" in code
    assert "!entry.EventId" in code
    assert "return entry.EventId" in code
    assert 'type = "Mutation"' in resolver
    assert 'name = "APPSYNC_JS"' in resolver
    assert generate(payload) == tree
    hcl2.loads(source)
    hcl2.loads(resolver)


def test_multiple_fields_share_one_bus_data_source():
    payload = architecture()
    payload["resources"][0]["config"]["schema_definition"] = (
        "type Query { _noop: String } "
        "type Mutation { probe(input: EventDetailInput!): ID, "
        "second(payload: EventDetailInput!): ID } "
        "input EventDetailInput { message: String }"
    )
    second = deepcopy(payload["connections"][0])
    second["connection_config"] = {
        "field_name": "second",
        "event_source": "com.example.other",
        "detail_type": "OtherEvent",
        "detail_argument": "payload",
    }
    payload["connections"].append(second)
    tree = generate(payload)
    assert len([p for p in tree if "/eventbridge_datasource_" in p]) == 1
    assert len([p for p in tree if "/eventbridge_resolver_" in p]) == 2
    assert 'detail: ctx.args["payload"]' in resolver_code(
        tree, "/eventbridge_resolver_Mutation_second_"
    )
    payload["connections"].reverse()
    assert generate(payload) == tree
    payload["connections"].append(deepcopy(second))
    assert generate(payload) == tree


def test_multiple_buses_have_distinct_roles_and_field_conflicts_fail():
    payload = architecture()
    payload["resources"][0]["config"]["schema_definition"] = (
        "type Query { _noop: String } "
        "type Mutation { probe(input: EventDetailInput!): ID, "
        "second(input: EventDetailInput!): ID } "
        "input EventDetailInput { message: String }"
    )
    bus = deepcopy(payload["resources"][1])
    bus.update(id="other", name="other-bus")
    bus["config"]["bus_name"] = "other-bus"
    payload["resources"].append(bus)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="other-bus", target_id="other")
    connection["connection_config"]["field_name"] = "second"
    payload["connections"].append(connection)
    tree = generate(payload)
    assert len([p for p in tree if "/eventbridge_datasource_" in p]) == 2
    assert "module.other-bus.event_bus_arn" in "\n".join(tree.values())
    payload["connections"][0]["connection_config"]["field_name"] = "second"
    with pytest.raises(
        InvalidConnectionConfigError, match="multiple EventBridge resolvers"
    ):
        generate(payload)


@pytest.mark.parametrize(
    "other_architecture",
    [lambda_architecture, dynamodb_architecture, opensearch_architecture],
)
def test_other_data_sources_cannot_resolve_same_field(other_architecture):
    payload = other_architecture()
    bus = deepcopy(architecture()["resources"][1])
    bus.update(id="bus", name="events")
    payload["resources"].append(bus)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(target="events", target_id="bus", connection_type="resolves_with")
    connection["connection_config"]["type_name"] = "Query"
    payload["connections"].append(connection)
    with pytest.raises(
        InvalidConnectionConfigError, match="multiple data-source resolvers"
    ):
        generate(payload)


def test_missing_schema_rejected():
    payload = architecture()
    payload["resources"][0]["config"].pop("schema_definition")
    with pytest.raises(InvalidConnectionConfigError, match="GraphQL schema definition"):
        generate(payload)


@pytest.mark.parametrize(
    "settings",
    [
        {},
        {"field_name": "probe", "event_source": "", "detail_type": "Changed"},
        {"field_name": "probe", "event_source": "aws.ec2", "detail_type": "Changed"},
        {"field_name": "probe", "event_source": "app", "detail_type": ""},
        {"field_name": "bad-name", "event_source": "app", "detail_type": "Changed"},
        {"field_name": "__schema", "event_source": "app", "detail_type": "Changed"},
        {
            "field_name": "probe",
            "event_source": "app",
            "detail_type": "Changed",
            "detail_argument": "__input",
        },
        {"field_name": "probe", "event_source": "x" * 257, "detail_type": "Changed"},
        {"field_name": "probe", "event_source": "app", "detail_type": "x" * 129},
    ],
)
def test_invalid_config_rejected(settings):
    with pytest.raises(ValidationError):
        AppSyncEventBridgeConfig.model_validate(settings)


@given(
    source=st.text(alphabet='abc.xyz/"', min_size=1, max_size=32).filter(
        lambda value: value.strip() and not value.startswith("aws.")
    ),
    detail_type=st.text(alphabet='abc XYZ"', min_size=1, max_size=32).filter(
        lambda value: value.strip()
    ),
)
def test_event_metadata_is_escaped_in_resolver(source, detail_type):
    payload = architecture()
    payload["connections"][0]["connection_config"].update(
        event_source=source, detail_type=detail_type
    )
    code = resolver_code(generate(payload))
    assert f"source: {json.dumps(source)}" in code
    assert f"detailType: {json.dumps(detail_type)}" in code


@needs_terraform
@pytest.mark.parametrize("custom_bus", [False, True])
def test_appsync_eventbridge_project_validates(tmp_path, custom_bus):
    payload = architecture()
    if custom_bus:
        payload["resources"][1]["config"]["bus_name"] = "application-bus"
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
