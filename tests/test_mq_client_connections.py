"""ActiveMQ client bindings select TLS endpoints without copying broker credentials."""

import json
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.generators.hcl_renderer import HCLRenderer
from app.models.connection_configs.mq import MQ_PROTOCOL_SCHEMES, MqClientConfig
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.mq_client import MqClientHandler
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)


def architecture(source=ServiceType.LAMBDA, protocol="amqp"):
    payload = connection_architecture(resolve_spec(source, ServiceType.MQ, None, {}))
    payload["connections"][0]["connection_config"] = {"protocol": protocol}
    return payload


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


def generate(payload):
    return CodeGenerator().generate(project(payload))


@given(
    source=st.sampled_from([ServiceType.LAMBDA, ServiceType.ECS]),
    protocol=st.sampled_from(list(MQ_PROTOCOL_SCHEMES)),
    mode=st.sampled_from(["SINGLE_INSTANCE", "ACTIVE_STANDBY_MULTI_AZ"]),
)
def test_bindings_use_typed_native_endpoints_without_iam_or_credentials(
    source, protocol, mode
):
    payload = architecture(source, protocol)
    payload["resources"][1]["config"]["deployment_mode"] = mode
    ir = project(payload)
    contribution = MqClientHandler().handle(ir.connections[0], ir)
    assert contribution.iam == []
    assert contribution.resources == []
    assert len(contribution.inputs) == 1
    assert contribution.inputs[0].type == "list(string)"
    assert (
        contribution.inputs[0].value
        == f"module.target-resource.client_{protocol}_endpoints"
    )
    assert all("password" not in output.value for output in contribution.outputs)
    tree = generate(payload)
    text = "\n".join(tree.values())
    assert f"endpoints = var.mq_target-resource_{protocol}_endpoints" in text
    assert "for broker in aws_mq_broker.target-resource.instances" in text
    assert "tls = true" in text
    assert "aws_lambda_event_source_mapping" not in text
    payload["connections"] = []
    baseline = generate(payload)
    policy_path = "connection-check/iam-policies/source-resource-policy.json"
    assert tree[policy_path] == baseline[policy_path]
    source_outputs = "\n".join(
        content
        for path, content in tree.items()
        if "/source-resource/" in path and path.endswith("outputs.tf")
    )
    assert "password" not in source_outputs
    assert "username" not in source_outputs
    preview = ConnectionPreviewer().preview_all(ir)[0]
    assert any("failover" in issue.message for issue in preview.issues)


@needs_terraform
@pytest.mark.parametrize("protocol", list(MQ_PROTOCOL_SCHEMES))
def test_terraform_expression_selects_all_instances_independent_of_endpoint_order(
    protocol, tmp_path
):
    ir = project(architecture(protocol=protocol))
    expression = MqClientHandler().handle(ir.connections[0], ir).outputs[0].value
    instances = [
        {
            "endpoints": [
                f"{scheme}://broker-{index}:1234"
                for scheme in reversed(list(MQ_PROTOCOL_SCHEMES.values()))
            ]
            + ["https://console:8162", "tcp://plaintext:61616", "amqp://plaintext:5672"]
        }
        for index in [2, 1, 2]
    ]
    literal = HCLRenderer().render_expression(json.dumps(instances))
    expression = expression.replace(
        "aws_mq_broker.target-resource.instances", f"jsondecode({literal})"
    )
    result = subprocess.run(
        ["terraform", "console", "-no-color"],
        input=f"jsonencode({expression})\n",
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(json.loads(result.stdout)) == [
        f"{MQ_PROTOCOL_SCHEMES[protocol]}://broker-{index}:1234" for index in [1, 2]
    ]


@pytest.mark.parametrize(
    "protocol", ["http", "tcp", "amqps", "AMQP", "*", "", "rabbitmq"]
)
def test_only_supported_activemq_protocols_are_accepted(protocol):
    with pytest.raises(ValidationError):
        MqClientConfig(protocol=protocol)


def test_default_connection_and_protocol_schema():
    spec = resolve_spec(ServiceType.ECS, ServiceType.MQ, None, {})
    assert spec.connection_type == "connects_to"
    assert spec.config_model().protocol == "amqp"
    field = spec.config_model.get_field_schema()[0]
    assert field.default == "amqp"
    assert {option.value for option in field.options} == set(MQ_PROTOCOL_SCHEMES)
    with pytest.raises(ValidationError):
        MqClientConfig(password="must-not-be-copied")


@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_multiple_protocols_and_brokers_aggregate_deterministically(source):
    payload = architecture(source)
    other_protocol = deepcopy(payload["connections"][0])
    other_protocol["connection_config"]["protocol"] = "openwire"
    broker = deepcopy(payload["resources"][1])
    broker.update(id="other-broker", name="other-broker")
    payload["resources"].append(broker)
    other_broker = deepcopy(other_protocol)
    other_broker.update(target="other-broker", target_id="other-broker")
    payload["connections"].extend([other_protocol, other_broker])
    tree = generate(payload)
    text = "\n".join(tree.values())
    assert "mq_target-resource_amqp_client" in text
    assert "mq_target-resource_openwire_client" in text
    assert "mq_other-broker_openwire_client" in text
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_endpoint_bindings_compose_with_existing_secret_delivery(source):
    payload = architecture(source)
    kind = "reads_secret" if source == ServiceType.LAMBDA else "injects_secret"
    secret_payload = connection_architecture(
        resolve_spec(source, ServiceType.SECRETS_MANAGER, kind, {})
    )
    secret = secret_payload["resources"][1]
    secret.update(id="credentials", name="credentials")
    payload["resources"].append(secret)
    connection = secret_payload["connections"][0]
    connection.update(target="credentials", target_id="credentials")
    payload["connections"].append(connection)
    tree = generate(payload)
    text = "\n".join(tree.values())
    assert "mq_target-resource_amqp_client" in text
    assert "secretsmanager:GetSecretValue" in text
    assert "mq:DescribeBroker" not in text
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_shared_broker_has_one_protocol_output_for_distinct_consumers():
    payload = architecture()
    other = architecture(ServiceType.ECS)
    resource = other["resources"][0]
    resource.update(id="ecs-client", name="ecs-client")
    payload["resources"].append(resource)
    connection = other["connections"][0]
    connection.update(source="ecs-client", source_id="ecs-client")
    payload["connections"].append(connection)
    tree = generate(payload)
    assert "\n".join(tree.values()).count('output "client_amqp_endpoints"') == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


@needs_terraform
@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_all_protocols_validate_without_dependency_cycles(source, tmp_path):
    payload = architecture(source)
    payload["connections"] = [
        {**payload["connections"][0], "connection_config": {"protocol": protocol}}
        for protocol in MQ_PROTOCOL_SCHEMES
    ]
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
