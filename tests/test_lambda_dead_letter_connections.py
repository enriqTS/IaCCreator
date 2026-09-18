"""Lambda dead-letter bindings preserve scoped permissions and existing defaults."""

import json
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from tests.generator_helpers import connection_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate, project
from tests.test_kms_access_integration import add_key


def architecture(target=ServiceType.SQS):
    return connection_architecture(
        resolve_spec(ServiceType.LAMBDA, target, "dead_letters_to", {})
    )


@given(
    target=st.sampled_from([ServiceType.SQS, ServiceType.SNS]), encrypted=st.booleans()
)
def test_native_binding_permissions_and_idempotence(target, encrypted):
    payload = architecture(target)
    if encrypted:
        add_key(payload)
    tree = generate(payload)
    function = next(v for k, v in tree.items() if k.endswith("/lambda.tf"))
    assert "target_arn = var.dead_letter_target_arn" in function
    assert '!endswith(var.dead_letter_target_arn, ".fifo")' in function
    assert "depends_on = [aws_iam_role_policy.source-resource_policy]" in function
    text = "\n".join(tree.values())
    assert (
        f"module.target-resource.{'queue' if target == ServiceType.SQS else 'topic'}_arn"
        in text
    )
    policy = json.loads(
        tree["connection-check/iam-policies/source-resource-policy.json"]
    )
    grants = [
        s
        for s in policy["Statement"]
        if s["Resource"] == "${var.dead_letter_target_arn}"
    ]
    assert len(grants) == 1
    assert grants[0]["Action"] == (
        ["sqs:SendMessage"] if target == ServiceType.SQS else ["sns:Publish"]
    )
    kms = [s for s in policy["Statement"] if "kms:Decrypt" in s["Action"]]
    assert len(kms) == int(encrypted)
    if encrypted:
        assert kms[0]["Resource"] == "${var.kms_access_target-resource_arn}"
    assert "aws_lambda_function_event_invoke_config" not in text
    assert "aws_sqs_queue_redrive_policy" not in text
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


@pytest.mark.parametrize("target", [ServiceType.SQS, ServiceType.SNS])
def test_fifo_destinations_rejected(target):
    payload = architecture(target)
    payload["resources"][1]["config"][
        "fifo_queue" if target == ServiceType.SQS else "fifo_topic"
    ] = True
    with pytest.raises(InvalidConnectionConfigError, match="not FIFO"):
        generate(payload)


def test_conflicting_destination_kinds_rejected():
    payload = architecture()
    other = architecture(ServiceType.SNS)
    resource = other["resources"][1]
    resource.update(id="topic", name="failure-topic")
    payload["resources"].append(resource)
    edge = other["connections"][0]
    edge.update(target="failure-topic", target_id="topic")
    payload["connections"].append(edge)
    with pytest.raises(InvalidConnectionConfigError, match="only one"):
        generate(payload)


def test_external_destination_conflict_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["dead_letter_target_arn"] = (
        "arn:aws:sqs:us-east-1:123456789012:external"
    )
    with pytest.raises(
        InvalidConnectionConfigError, match="external dead_letter_target_arn"
    ):
        generate(payload)


@pytest.mark.parametrize(
    "target,kind", [(ServiceType.SQS, "sends_to"), (ServiceType.SNS, "publishes_to")]
)
def test_existing_default_remains_and_composes(target, kind):
    assert resolve_spec(ServiceType.LAMBDA, target, None, {}).connection_type == kind
    payload = architecture(target)
    edge = deepcopy(payload["connections"][0])
    edge["connection_type"] = kind
    payload["connections"].append(edge)
    tree = generate(payload)
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_preview_explains_async_scope():
    message = " ".join(
        issue.message
        for issue in ConnectionPreviewer()
        .preview_all(project(architecture()))[0]
        .issues
    )
    assert "asynchronous" in message
    assert "SQS event-source" in message
    assert "DeadLetterErrors" in message


@needs_terraform
@pytest.mark.parametrize("target", [ServiceType.SQS, ServiceType.SNS])
@pytest.mark.parametrize("encryption", ["none", "managed", "external"])
def test_projects_validate(target, encryption, tmp_path):
    payload = architecture(target)
    if encryption == "managed":
        add_key(payload)
    elif encryption == "external":
        payload["resources"][1]["config"]["kms_master_key_id"] = "alias/external-key"
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
