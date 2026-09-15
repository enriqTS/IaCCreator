"""MSK topic access keeps Kafka data permissions separate from administration."""

import json
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.msk import MskTopicReadConfig, MskTopicWriteConfig
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
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


def architecture(source=ServiceType.LAMBDA, kind="reads_from"):
    return connection_architecture(resolve_spec(source, ServiceType.MSK, kind, {}))


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


def generate(payload):
    return CodeGenerator().generate(project(payload))


def grants(tree):
    policy = json.loads(
        tree["connection-check/iam-policies/source-resource-policy.json"]
    )
    return {
        action: statement["Resource"]
        for statement in policy["Statement"]
        for action in statement["Action"]
        if action.startswith("kafka-cluster:")
    }


@given(
    source=st.sampled_from([ServiceType.LAMBDA, ServiceType.ECS]),
    kind=st.sampled_from(["reads_from", "writes_to"]),
    topic=st.from_regex(r"[a-z][A-Za-z0-9._-]{0,40}", fullmatch=True),
    group=st.from_regex(r"[a-z][A-Za-z0-9._-]{0,40}", fullmatch=True),
)
def test_client_permissions_are_scoped_to_cluster_topic_and_group(
    source, kind, topic, group
):
    payload = architecture(source, kind)
    config = {"topic_name": topic}
    if kind == "reads_from":
        config["consumer_group"] = group
    payload["connections"][0]["connection_config"] = config
    tree = generate(payload)
    expected = {
        "kafka-cluster:Connect": "${var.msk_target-resource_cluster_arn}",
        "kafka-cluster:DescribeCluster": "${var.msk_target-resource_cluster_arn}",
        "kafka-cluster:DescribeTopic": "${var.msk_target-resource_topic_arn_prefix}/"
        + topic,
        "kafka-cluster:ReadData"
        if kind == "reads_from"
        else "kafka-cluster:WriteData": "${var.msk_target-resource_topic_arn_prefix}/"
        + topic,
    }
    if kind == "reads_from":
        expected.update(
            {
                "kafka-cluster:DescribeGroup": "${var.msk_target-resource_group_arn_prefix}/"
                + group,
                "kafka-cluster:AlterGroup": "${var.msk_target-resource_group_arn_prefix}/"
                + group,
            }
        )
    assert grants(tree) == expected
    text = "\n".join(tree.values())
    assert (
        'replace(aws_msk_cluster.target-resource.arn, ":cluster/", ":topic/")' in text
    )
    assert "aws_msk_cluster.target-resource.bootstrap_brokers_sasl_iam" in text
    assert 'security_protocol = "SASL_SSL"' in text
    assert 'sasl_mechanism = "OAUTHBEARER"' in text
    assert "iam = true" in text
    assert "unauthenticated = false" in text
    assert 'client_broker = "TLS"' in text
    assert ("enable_idempotence = false" in text) == (kind == "writes_to")
    assert "aws_lambda_event_source_mapping" not in text
    assert "aws_msk_cluster_policy" not in text
    if source == ServiceType.ECS:
        assert "task_role_arn = aws_iam_role.source-resource_role.arn" in text
    assert ConnectionPreviewer().preview_all(project(payload))[0].issues


@pytest.mark.parametrize(
    "name",
    ["", "*", "a?", "a/b", "a:b", ".", "..", "__consumer_offsets", "a b", "a" * 250],
)
def test_names_cannot_expand_iam_resource_scope(name):
    with pytest.raises(ValidationError):
        MskTopicWriteConfig(topic_name=name)
    with pytest.raises(ValidationError):
        MskTopicReadConfig(topic_name="records", consumer_group=name)


@pytest.mark.parametrize("version", [None, "", "2.6.3", "2.7.0", "1.0.0"])
def test_incompatible_kafka_versions_fail_before_generation(version):
    payload = architecture()
    payload["resources"][1]["config"]["kafka_version"] = version
    with pytest.raises(InvalidConnectionConfigError, match="2.7.1"):
        generate(payload)


@pytest.mark.parametrize("version", ["2.7.1", "2.8.2", "3.8.x", "4.0.x", "10.0"])
def test_iam_version_guards_accept_versions_meeting_minimum(version):
    payload = architecture()
    payload["resources"][1]["config"]["kafka_version"] = version
    text = "\n".join(generate(payload).values())
    assert "var.kafka_version" in text
    assert "self.kafka_version" in text


@pytest.mark.parametrize(
    "override",
    [
        {"subnet_ids": []},
        {"subnet_ids": ["subnet-a"]},
        {"subnet_ids": ["subnet-a", "subnet-b", "subnet-a"]},
        {"security_group_ids": []},
        {"number_of_broker_nodes": 3},
        {"number_of_broker_nodes": 0},
        {"number_of_broker_nodes": None},
    ],
)
def test_missing_or_inconsistent_broker_placement_is_rejected(override):
    payload = architecture()
    payload["resources"][1]["config"].update(override)
    with pytest.raises(InvalidConnectionConfigError, match="broker"):
        generate(payload)


@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_topics_groups_and_access_modes_aggregate_deterministically(source):
    payload = architecture(source)
    write = deepcopy(payload["connections"][0])
    write["connection_type"] = "writes_to"
    write["connection_config"] = {"topic_name": "audit-events"}
    other = deepcopy(payload["connections"][0])
    other["connection_config"]["consumer_group"] = "other-readers"
    payload["connections"].extend([write, other])
    tree = generate(payload)
    text = "\n".join(tree.values())
    assert text.count("iam = true") == 1
    assert "_group_arn_prefix}/other-readers" in text
    assert "_topic_arn_prefix}/audit-events" in text
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


def test_default_read_schema_requires_topic_and_group():
    spec = resolve_spec(ServiceType.LAMBDA, ServiceType.MSK, None, {})
    assert spec.connection_type == "reads_from"
    assert {
        field.key for field in spec.config_model.get_field_schema() if field.required
    } == {"topic_name", "consumer_group"}
    with pytest.raises(ValidationError):
        MskTopicReadConfig(topic_name="records")
    with pytest.raises(ValidationError):
        MskTopicWriteConfig(topic_name="records", consumer_group="readers")


def test_unconnected_cluster_has_broker_placement_without_forcing_iam():
    payload = architecture()
    payload["connections"] = []
    text = "\n".join(generate(payload).values())
    assert "broker_node_group_info" in text
    assert "client_subnets = var.subnet_ids" in text
    assert "security_groups = var.security_group_ids" in text
    assert "client_authentication" not in text


@needs_terraform
@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_mixed_topic_access_validates_without_cycles(source, tmp_path):
    payload = architecture(source)
    write = deepcopy(payload["connections"][0])
    write["connection_type"] = "writes_to"
    write["connection_config"] = {"topic_name": "output-records"}
    payload["connections"].append(write)
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
