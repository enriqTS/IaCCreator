"""Step Functions Lambda connections replace Pass states with executable tasks."""

import json
import shutil
import subprocess
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.step_functions_lambda import lambda_workflow_locals
from app.models.connection_configs.workflows import StepFunctionsLambdaConfig
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
from tests.test_secret_connections import architecture as secret_architecture


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.STEP_FUNCTIONS, ServiceType.LAMBDA, None, {})
    )


def test_task_replaces_pass_and_grants_invoke():
    tree = generate(architecture())
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    task = next(
        value for path, value in tree.items() if path.endswith("/lambda_tasks.tf")
    )
    policy = next(
        value
        for path, value in tree.items()
        if path.endswith("/lambda_tasks_policy.tf")
    )
    assert "definition = local.lambda_workflow_definition" in machine
    assert "local.lambda_tasks_valid" in machine
    assert 'Type = "Task", Resource = arn' in task
    assert "var.workflow_lambda_0_arn" in task
    assert '"lambda:InvokeFunction"' in policy
    assert "var.workflow_lambda_0_arn" in policy
    assert "module.target-resource.function_arn" in "\n".join(tree.values())
    assert generate(architecture()) == tree


def test_missing_execution_role_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["role_arn"] = ""
    with pytest.raises(InvalidConnectionConfigError, match="execution role ARN"):
        generate(payload)


def test_invalid_placeholder_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["definition"] = (
        '{"StartAt":"Pass","States":{"Pass":{"Type":"Task","End":true}}}'
    )
    with pytest.raises(InvalidConnectionConfigError, match="Pass state"):
        generate(payload)


def test_same_state_cannot_bind_two_functions():
    payload = architecture()
    second = deepcopy(payload["resources"][1])
    second.update(id="second", name="second-function")
    payload["resources"].append(second)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="second-function", target_id="second")
    payload["connections"].append(connection)
    with pytest.raises(InvalidConnectionConfigError, match="same workflow state"):
        generate(payload)


def mixed_architecture():
    payload = architecture()
    payload["resources"][0]["config"]["definition"] = json.dumps(
        {
            "StartAt": "Read",
            "States": {
                "Read": {"Type": "Pass", "Next": "Invoke"},
                "Invoke": {"Type": "Pass", "End": True},
            },
        }
    )
    payload["connections"][0]["connection_config"] = {"state_name": "Invoke"}
    secret_payload = secret_architecture(ServiceType.STEP_FUNCTIONS)
    secret = deepcopy(secret_payload["resources"][1])
    secret.update(id="secret", name="secret-resource")
    payload["resources"].append(secret)
    connection = deepcopy(secret_payload["connections"][0])
    connection.update(
        source="source-resource",
        source_id="src",
        target="secret-resource",
        target_id="secret",
    )
    connection["connection_config"] = {"state_name": "Read"}
    payload["connections"].append(connection)
    return payload


def test_secret_and_lambda_states_compose():
    payload = mixed_architecture()
    tree = generate(payload)
    payload["connections"].reverse()
    assert generate(payload) == tree
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    task = next(
        value for path, value in tree.items() if path.endswith("/lambda_tasks.tf")
    )
    assert "local.secret_workflow_definition" in task
    assert "local.secret_tasks_valid" in machine
    assert "local.lambda_tasks_valid" in machine
    assert "aws_iam_role_policy.runtime_secrets" in machine
    assert "aws_iam_role_policy.lambda_tasks" in machine


def test_secret_and_lambda_cannot_share_state():
    payload = architecture()
    secret_payload = secret_architecture(ServiceType.STEP_FUNCTIONS)
    secret = deepcopy(secret_payload["resources"][1])
    secret.update(id="secret", name="secret-resource")
    payload["resources"].append(secret)
    connection = deepcopy(secret_payload["connections"][0])
    connection.update(
        source="source-resource",
        source_id="src",
        target="secret-resource",
        target_id="secret",
    )
    payload["connections"].append(connection)
    with pytest.raises(
        InvalidConnectionConfigError, match="both Lambda and Secrets Manager"
    ):
        generate(payload)


def test_invalid_state_name_rejected():
    with pytest.raises(ValidationError):
        StepFunctionsLambdaConfig(state_name="${unsafe}")


def test_lambda_task_keeps_paths_and_transitions(tmp_path):
    if shutil.which("terraform") is None:
        pytest.skip("terraform binary not installed")
    definition = {
        "StartAt": "Invoke",
        "Comment": "Keep workflow settings",
        "States": {
            "Invoke": {
                "Type": "Pass",
                "Next": "Done",
                "InputPath": "$.request",
                "ResultPath": "$.answer",
                "Result": "placeholder",
            },
            "Done": {"Type": "Succeed"},
        },
    }
    content = HCLRenderer().render_variable(
        "definition", "string", "Workflow", default=json.dumps(definition)
    )
    content += lambda_workflow_locals(
        {"Invoke": Expr('"arn:aws:lambda:us-east-1:123456789012:function:example"')},
        False,
    )
    (tmp_path / "main.tf").write_text(content)
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input="jsonencode({valid = local.lambda_tasks_valid, workflow = jsondecode(local.lambda_workflow_definition)})\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(json.loads(result.stdout.strip()))
    assert output["valid"] is True
    assert output["workflow"]["Comment"] == "Keep workflow settings"
    assert output["workflow"]["States"]["Done"] == {"Type": "Succeed"}
    state = output["workflow"]["States"]["Invoke"]
    assert state["Type"] == "Task"
    assert state["Resource"].endswith(":function:example")
    assert state["Next"] == "Done"
    assert state["InputPath"] == "$.request"
    assert state["ResultPath"] == "$.answer"
    assert "Result" not in state


@needs_terraform
def test_step_functions_lambda_validates(tmp_path):
    _write_tree(tmp_path, generate(architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)


@needs_terraform
def test_mixed_workflow_validates(tmp_path):
    _write_tree(tmp_path, generate(mixed_architecture()))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
