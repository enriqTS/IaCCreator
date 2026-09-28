"""SNS Firehose subscriptions have stream-scoped delivery roles."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.models.connection_configs.sns_firehose import SnsFirehoseConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from tests.generator_helpers import connection_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.SNS, ServiceType.KINESIS_FIREHOSE, None, {})
    )


def test_subscription_has_scoped_delivery_role():
    tree = generate(architecture())
    subscription = next(
        value
        for path, value in tree.items()
        if path.endswith("/subscription_source-resource.tf")
    )
    assert 'protocol = "firehose"' in subscription
    assert "var.source_resource_topic_arn" in subscription
    assert "aws_kinesis_firehose_delivery_stream.target-resource.arn" in subscription
    assert (
        "subscription_role_arn = aws_iam_role.source_resource_sns_delivery.arn"
        in subscription
    )
    assert '"firehose:PutRecord"' in subscription
    assert '"firehose:PutRecordBatch"' in subscription
    assert "sns.amazonaws.com" in subscription
    assert "raw_message_delivery = false" in subscription
    assert generate(architecture()) == tree


def test_raw_delivery_is_configurable():
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"raw_message_delivery": True}
    tree = generate(payload)
    subscription = next(
        value
        for path, value in tree.items()
        if path.endswith("/subscription_source-resource.tf")
    )
    assert "raw_message_delivery = true" in subscription


def test_fifo_topic_rejected():
    payload = architecture()
    payload["resources"][0]["config"].update(fifo_topic=True, topic_name="events.fifo")
    with pytest.raises(Exception, match="standard SNS topic"):
        generate(payload)


def test_invalid_setting_rejected():
    with pytest.raises(ValidationError):
        SnsFirehoseConfig(raw_message_delivery="unexpected")


def test_multiple_topics_keep_separate_subscriptions():
    payload = architecture()
    topic = deepcopy(payload["resources"][0])
    topic.update(id="src-two", name="other-topic")
    topic["config"]["topic_name"] = "other-topic"
    payload["resources"].append(topic)
    connection = deepcopy(payload["connections"][0])
    connection.update(source="other-topic", source_id="src-two")
    payload["connections"].append(connection)
    tree = generate(payload)
    assert any(path.endswith("/subscription_source-resource.tf") for path in tree)
    assert any(path.endswith("/subscription_other-topic.tf") for path in tree)


@needs_terraform
def test_sns_firehose_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
