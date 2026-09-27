"""SNS targets use publish roles that compose with encryption and existing policies."""

from copy import deepcopy

import pytest

from app.exceptions import InvalidConnectionConfigError
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
from tests.test_kms_access_integration import add_key


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.EVENTBRIDGE, ServiceType.SNS, None, {})
    )


@pytest.mark.parametrize("encryption", ["none", "managed", "external"])
def test_publish_role_is_scoped_and_key_grants_are_role_owned(encryption):
    payload = architecture()
    if encryption == "managed":
        add_key(payload)
    elif encryption == "external":
        payload["resources"][1]["config"]["kms_master_key_id"] = "alias/topic-key"
    payload["connections"][0]["connection_config"]["input"] = '{"kind":"job"}'
    tree = generate(payload)
    target = next(v for k, v in tree.items() if "/topic_" in k)
    assert '"sns:Publish"' in target
    assert "var.topic_" in target
    assert "events.amazonaws.com" in target
    assert "aws_cloudwatch_event_rule.source-resource.arn" in target
    assert "role_arn = aws_iam_role.topic_" in target
    assert "!endswith(var.topic_" in target
    assert ("kms:Decrypt" in target) == (encryption != "none")
    if encryption != "none":
        assert "kms:GenerateDataKey*" in target
    text = "\n".join(tree.values())
    assert "module.target-resource.topic_arn" in text
    assert "aws_sns_topic_policy" not in text
    assert "aws_iam_role.source-resource_role" not in text
    assert "states:StartExecution" not in text
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


def test_fifo_topic_rejected():
    payload = architecture()
    payload["resources"][1]["config"]["fifo_topic"] = True
    with pytest.raises(InvalidConnectionConfigError, match="standard SNS topic"):
        generate(payload)


def test_target_identifier_conflict_across_services_rejected():
    payload = architecture()
    payload["connections"][0]["connection_config"]["target_id"] = "shared"
    other = connection_architecture(
        resolve_spec(ServiceType.EVENTBRIDGE, ServiceType.STEP_FUNCTIONS, None, {})
    )
    destination = deepcopy(other["resources"][1])
    destination.update(id="workflow", name="workflow")
    payload["resources"].append(destination)
    edge = deepcopy(other["connections"][0])
    edge.update(
        target="workflow",
        target_id="workflow",
        connection_config={"target_id": "shared"},
    )
    payload["connections"].append(edge)
    with pytest.raises(InvalidConnectionConfigError, match="uniquely"):
        generate(payload)


@needs_terraform
@pytest.mark.parametrize("encryption", ["none", "managed", "external"])
def test_topic_target_validates(encryption, tmp_path):
    payload = architecture()
    if encryption == "managed":
        add_key(payload)
    elif encryption == "external":
        payload["resources"][1]["config"]["kms_master_key_id"] = "alias/topic-key"
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
