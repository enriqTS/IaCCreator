"""EventBridge Batch targets reference a queue and one generated job definition."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.eventbridge_batch import EventBridgeBatchConfig
from app.models.input_models import ServiceType
from app.models.input_models.batch_config import BatchConfig
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
        resolve_spec(ServiceType.EVENTBRIDGE, ServiceType.BATCH, None, {})
    )


def test_target_uses_native_queue_definition_and_scoped_submit_role():
    tree = generate(architecture())
    target = next(v for k, v in tree.items() if "/batch_" in k)
    assert '"batch:SubmitJob"' in target
    assert "batch_target" in target
    assert "job_definition = var.batch_" in target
    assert "module.target-resource.job_queue_arn" in "\n".join(tree.values())
    assert "module.batch-job.job_definition_arn" in "\n".join(tree.values())
    queue = tree["connection-check/modules/compute/batch/target-resource/batch.tf"]
    assert 'resource "aws_batch_job_queue" "target-resource_queue"' in queue
    assert "aws_batch_compute_environment.target-resource.arn" in queue
    assert generate(architecture()) == tree


def test_missing_definition_and_unsupported_compute_environment_rejected():
    for change in ({"job_definition_name": "missing"},):
        payload = architecture()
        payload["connections"][0]["connection_config"].update(change)
        with pytest.raises(InvalidConnectionConfigError):
            generate(payload)
    payload = architecture()
    payload["resources"][1]["config"]["batch_compute_environment_type"] = "MANAGED"
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)
    payload = architecture()
    payload["resources"][1]["config"]["service_role_arn"] = None
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("array_size", 1),
        ("array_size", 10001),
        ("job_attempts", 0),
        ("job_attempts", 11),
    ],
)
def test_batch_target_bounds(field, value):
    with pytest.raises(ValidationError):
        EventBridgeBatchConfig(job_definition_name="batch-job", **{field: value})


def test_target_id_conflict_rejects_changed_definition():
    payload = architecture()
    other = deepcopy(payload["connections"][0])
    other["connection_config"]["job_attempts"] = 2
    payload["connections"].append(other)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize("name", ["bad/name", "x" * 129])
def test_invalid_queue_names_rejected(name):
    with pytest.raises(ValidationError):
        BatchConfig(job_queue_name=name)


@pytest.mark.parametrize("priority", [-1, 1001])
def test_invalid_queue_priorities_rejected(priority):
    with pytest.raises(ValidationError):
        BatchConfig(job_queue_priority=priority)


def test_array_and_attempt_settings_are_native():
    payload = architecture()
    payload["connections"][0]["connection_config"].update(
        array_size=4, job_attempts=3, job_name="nightly-job"
    )
    target = next(v for k, v in generate(payload).items() if "/batch_" in k)
    assert "array_size = 4" in target
    assert "job_attempts = 3" in target
    assert 'job_name = "nightly-job"' in target


@needs_terraform
def test_batch_target_terraform_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
