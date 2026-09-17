"""ECS polling uses task-role permissions scoped to connected queues and keys."""

import json
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

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


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.SQS, ServiceType.ECS, None, {})
    )


@given(fifo=st.booleans(), encrypted=st.booleans())
def test_polling_grants_task_role_and_exports_native_queue(fifo, encrypted):
    payload = architecture()
    config = payload["resources"][0]["config"]
    config.update(fifo_queue=fifo, queue_name="jobs.fifo" if fifo else "jobs")
    if encrypted:
        config["kms_master_key_id"] = (
            "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
        )
    tree = generate(payload)
    policy = json.loads(
        tree["connection-check/iam-policies/target-resource-policy.json"]
    )
    statements = policy["Statement"]
    sqs = [s for s in statements if any(a.startswith("sqs:") for a in s["Action"])]
    assert len(sqs) == 1
    assert sqs[0]["Resource"] == "${var.sqs_source-resource_arn}"
    assert set(sqs[0]["Action"]) == {
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:ChangeMessageVisibility",
        "sqs:GetQueueAttributes",
    }
    kms = [s for s in statements if any(a.startswith("kms:") for a in s["Action"])]
    assert len(kms) == int(encrypted)
    if encrypted:
        assert kms[0]["Action"] == ["kms:Decrypt"]
        assert (
            kms[0]["Resource"]
            == "${data.aws_kms_key.kms_access_source-resource_arn.arn}"
        )
    text = "\n".join(tree.values())
    assert "task_role_arn = aws_iam_role.target-resource_role.arn" in text
    assert "module.source-resource.queue_arn" in text
    assert "module.source-resource.queue_url" in text
    assert 'split(":", var.sqs_source-resource_arn)[3]' in text
    assert "aws_lambda_event_source_mapping" not in text
    assert "sqs:SendMessage" not in text
    assert "sqs:PurgeQueue" not in text
    queue = "\n".join(v for k, v in tree.items() if "/source-resource/" in k)
    assert "module.target-resource" not in queue
    assert "aws_iam_role" not in queue
    payload["connections"] *= 2
    assert generate(payload) == tree


def test_multiple_queues_are_order_independent():
    payload = architecture()
    queue = deepcopy(payload["resources"][0])
    queue.update(id="other", name="other-queue")
    queue["config"]["queue_name"] = "other-queue"
    payload["resources"].append(queue)
    connection = deepcopy(payload["connections"][0])
    connection.update(source="other-queue", source_id="other")
    payload["connections"].append(connection)
    expected = generate(payload)
    payload["connections"].reverse()
    assert generate(payload) == expected
    policy = json.loads(
        expected["connection-check/iam-policies/target-resource-policy.json"]
    )
    assert {
        s["Resource"]
        for s in policy["Statement"]
        if "sqs:ReceiveMessage" in s["Action"]
    } == {
        "${var.sqs_source-resource_arn}",
        "${var.sqs_other-queue_arn}",
    }


def test_preview_explains_application_and_key_requirements():
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    message = " ".join(issue.message for issue in preview.issues)
    for text in (
        "poll",
        "delete",
        "visibility",
        "task role",
        "KMS",
        "network",
        "autoscaling",
    ):
        assert text in message


def test_managed_key_grants_only_decrypt_to_consumer():
    payload = architecture()
    add_key(payload, 0)
    tree = generate(payload)
    policy = json.loads(
        tree["connection-check/iam-policies/target-resource-policy.json"]
    )
    grants = [s for s in policy["Statement"] if "kms:Decrypt" in s["Action"]]
    assert len(grants) == 1
    assert grants[0]["Action"] == ["kms:Decrypt"]
    assert grants[0]["Resource"] == "${var.kms_access_source-resource_arn}"
    assert "module.encryption-key.key_arn" in "\n".join(tree.values())
    payload["connections"].reverse()
    assert generate(payload) == tree


@needs_terraform
@pytest.mark.parametrize("fifo", [False, True])
@pytest.mark.parametrize("encrypted", [False, True])
def test_polling_projects_validate_without_cycles(fifo, encrypted, tmp_path):
    payload = architecture()
    payload["resources"][0]["config"].update(
        fifo_queue=fifo, queue_name="jobs.fifo" if fifo else "jobs"
    )
    if encrypted:
        add_key(payload, 0)
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
