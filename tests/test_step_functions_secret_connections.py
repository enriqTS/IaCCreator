"""Executable secret tasks preserve workflow structure without Terraform plaintext."""

import json
import shutil
import subprocess
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.step_functions_secrets import secret_workflow_locals
from app.models.connection_configs.workflows import StepFunctionsSecretConfig
from app.models.input_models import ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from tests.test_secret_connections import architecture, project


def test_native_task_and_scoped_external_role_policy_are_generated():
    tree = CodeGenerator().generate(project(architecture(ServiceType.STEP_FUNCTIONS)))
    machine = next(
        content for path, content in tree.items() if path.endswith("/step-functions.tf")
    )
    tasks = next(
        content for path, content in tree.items() if path.endswith("/secret_tasks.tf")
    )
    assert "definition = local.secret_workflow_definition" in machine
    assert "depends_on = [aws_iam_role_policy.runtime_secrets]" in machine
    assert "precondition" in machine
    assert "aws-sdk:secretsmanager:getSecretValue" in tasks
    assert "SecretId = arn" in tasks
    assert "runtime_secret_0_arn" in tasks
    assert 'resource "aws_iam_role"' not in "\n".join(tree.values())
    assert "aws_secretsmanager_secret_version" not in "\n".join(tree.values())


@pytest.mark.parametrize("empty_config", [False, True])
def test_missing_execution_role_is_rejected(empty_config):
    payload = architecture(ServiceType.STEP_FUNCTIONS)
    payload["resources"][0]["config"].pop("role_arn")
    if empty_config:
        payload["resources"][0]["config"] = {}
    with pytest.raises(InvalidConnectionConfigError, match="service role ARN"):
        CodeGenerator().generate(project(payload))


def test_conflicting_state_bindings_are_rejected():
    payload = architecture(ServiceType.STEP_FUNCTIONS)
    secret = deepcopy(payload["resources"][1])
    secret.update(id="other", name="other-secret")
    payload["resources"].append(secret)
    payload["connections"].append(
        dict(payload["connections"][0], target="other-secret", target_id="other")
    )
    with pytest.raises(InvalidConnectionConfigError, match="same workflow state"):
        CodeGenerator().generate(project(payload))


@pytest.mark.parametrize(
    "definition",
    [
        "not json",
        "[]",
        '{"States":{}}',
        '{"StartAt":"Missing","States":{"Pass":{"Type":"Pass","End":true}}}',
        '{"StartAt":"Pass","States":{"Pass":{"Type":"Task","End":true}}}',
        '{"StartAt":"Pass","States":{"Pass":{"Type":"Pass","Next":"Missing"}}}',
        '{"StartAt":"Pass","States":{"Pass":{"Type":"Pass","End":true,"Next":"Pass"}}}',
        '{"StartAt":"Pass","QueryLanguage":"JSONata","States":{"Pass":{"Type":"Pass","End":true}}}',
        '{"StartAt":"Pass","States":{"Pass":{"Type":"Pass","End":true,"QueryLanguage":"JSONata"}}}',
        '{"StartAt":"Pass","States":{"Pass":{"Type":"Pass","End":true,"Parameters":{"value":1}}}}',
    ],
)
def test_invalid_or_unsupported_placeholders_are_rejected(definition):
    payload = architecture(ServiceType.STEP_FUNCTIONS)
    payload["resources"][0]["config"]["definition"] = definition
    with pytest.raises(InvalidConnectionConfigError):
        CodeGenerator().generate(project(payload))


def test_schema_legacy_resolution_and_sensitive_data_warning():
    spec = resolve_spec(
        ServiceType.STEP_FUNCTIONS, ServiceType.SECRETS_MANAGER, "reads_secret", {}
    )
    assert spec.config_model().state_name == "Pass"
    assert [field.key for field in spec.config_model.get_field_schema()] == [
        "state_name"
    ]
    assert (
        resolve_spec(ServiceType.STEP_FUNCTIONS, ServiceType.SECRETS_MANAGER, None, {})
        == spec
    )
    assert (
        resolve_spec(
            ServiceType.SECRETS_MANAGER, ServiceType.STEP_FUNCTIONS, "reads_secret", {}
        )
        is None
    )
    preview = ConnectionPreviewer().preview_all(
        project(architecture(ServiceType.STEP_FUNCTIONS))
    )[0]
    assert preview.issues[0].severity == "warning"
    assert "execution-history" in preview.issues[0].message


@pytest.mark.parametrize(
    "config",
    [
        {"state_name": ""},
        {"state_name": "a" * 81},
        {"state_name": "${injection}"},
        {"environment_name": "PASSWORD"},
    ],
)
def test_invalid_connection_config(config):
    with pytest.raises(ValidationError):
        StepFunctionsSecretConfig.model_validate(config)


def evaluate_workflow(tmp_path, definition, bindings, expression):
    if shutil.which("terraform") is None:
        pytest.skip("terraform binary not installed")
    content = HCLRenderer().render_variable(
        "definition", "string", "Original workflow", default=json.dumps(definition)
    )
    content += 'variable "partition" { default = "aws" }\n'
    content += (
        secret_workflow_locals(
            {name: Expr(json.dumps(arn)) for name, arn in bindings.items()}
        )
        .replace('data "aws_partition" "secret_tasks" {}\n', "")
        .replace("data.aws_partition.secret_tasks.partition", "var.partition")
    )
    (tmp_path / "main.tf").write_text(content)
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input=expression + "\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_rendered_tasks_preserve_transitions_paths_and_unrelated_states(tmp_path):
    workflow = {
        "StartAt": "ReadOne",
        "Comment": "Keep workflow settings",
        "TimeoutSeconds": 120,
        "States": {
            "ReadOne": {
                "Type": "Pass",
                "Next": "ReadTwo",
                "ResultPath": "$.first",
                "Result": "placeholder",
            },
            "ReadTwo": {
                "Type": "Pass",
                "Next": "Done",
                "InputPath": "$.request",
                "OutputPath": "$",
                "ResultPath": "$.second",
                "Comment": "Keep state settings",
            },
            "Done": {"Type": "Succeed"},
        },
    }
    output = evaluate_workflow(
        tmp_path,
        workflow,
        {"ReadOne": "arn:secret:first", "ReadTwo": "arn:secret:second"},
        "jsonencode({valid = local.secret_tasks_valid, definition = jsondecode(local.secret_workflow_definition)})",
    )
    result = json.loads(json.loads(output))
    assert result["valid"] is True
    rendered = result["definition"]
    assert rendered["StartAt"] == workflow["StartAt"]
    assert rendered["Comment"] == workflow["Comment"]
    assert rendered["TimeoutSeconds"] == 120
    assert rendered["States"]["Done"] == workflow["States"]["Done"]
    for name in ("ReadOne", "ReadTwo"):
        state = rendered["States"][name]
        assert state["Type"] == "Task"
        assert (
            state["Resource"]
            == "arn:aws:states:::aws-sdk:secretsmanager:getSecretValue"
        )
        assert "Result" not in state
        for field in ("Next", "ResultPath", "InputPath", "OutputPath", "Comment"):
            if field in workflow["States"][name]:
                assert state[field] == workflow["States"][name][field]
    assert rendered["States"]["ReadOne"]["Parameters"] == {
        "SecretId": "arn:secret:first"
    }
    assert rendered["States"]["ReadTwo"]["Parameters"] == {
        "SecretId": "arn:secret:second"
    }


@pytest.mark.parametrize(
    "state",
    [
        {"Type": "Pass", "End": True},
        {"Type": "Task", "End": True},
        {"Type": "Pass", "Next": "Missing"},
        {"Type": "Pass", "End": True, "Parameters": {}},
        {"Type": "Pass", "End": True, "QueryLanguage": "JSONata"},
    ],
)
def test_terraform_guard_revalidates_environment_definition_overrides(tmp_path, state):
    workflow = {"StartAt": "Pass", "States": {"Pass": state}}
    result = evaluate_workflow(
        tmp_path, workflow, {"Pass": "arn:secret"}, "local.secret_tasks_valid"
    )
    assert result == ("true" if state == {"Type": "Pass", "End": True} else "false")


def test_unconnected_workflow_is_unchanged():
    payload = architecture(ServiceType.STEP_FUNCTIONS)
    payload["connections"] = []
    tree = CodeGenerator().generate(project(payload))
    machine = next(
        content for path, content in tree.items() if path.endswith("/step-functions.tf")
    )
    assert "definition = var.definition" in machine
    assert not any("secret_tasks" in path or "runtime_secrets" in path for path in tree)
