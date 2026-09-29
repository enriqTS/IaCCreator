"""Step Functions DynamoDB connections perform scoped item operations."""

import json
import shutil
import subprocess
from copy import deepcopy

import hcl2
import pytest
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.step_functions_dynamodb import dynamodb_workflow_locals
from app.models.connection_configs.step_functions_dynamodb import (
    StepFunctionsDynamoDbConfig,
)
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
from tests.test_step_functions_sqs_connections import architecture as sqs_architecture


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.STEP_FUNCTIONS, ServiceType.DYNAMODB, None, {})
    )


@pytest.mark.parametrize(
    "operation,settings,expected_parameters",
    [
        ("get_item", {"consistent_read": True}, ("Key.$", "ConsistentRead")),
        ("put_item", {}, ("Item.$",)),
        (
            "update_item",
            {
                "update_expression": "SET #n = :v",
                "expression_attribute_names_path": "$.names",
                "expression_attribute_values_path": "$.values",
            },
            (
                "Key.$",
                "UpdateExpression",
                "ExpressionAttributeNames.$",
                "ExpressionAttributeValues.$",
            ),
        ),
        (
            "delete_item",
            {"condition_expression": "attribute_exists(id)"},
            ("Key.$", "ConditionExpression"),
        ),
    ],
)
def test_item_operation_and_scoped_policy_generated(
    operation, settings, expected_parameters
):
    payload = architecture()
    payload["connections"][0]["connection_config"] = {
        "operation": operation,
        **settings,
    }
    tree = generate(payload)
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    task = next(
        value for path, value in tree.items() if path.endswith("/dynamodb_tasks.tf")
    )
    policy = next(
        value
        for path, value in tree.items()
        if path.endswith("/dynamodb_tasks_policy.tf")
    )
    action = "".join(word.capitalize() for word in operation.split("_"))
    assert "definition = local.dynamodb_workflow_definition" in machine
    assert "local.dynamodb_tasks_valid" in machine
    assert f'operation = "{action[0].lower()}{action[1:]}"' in task
    assert "var.workflow_dynamodb_table_0_name" in task
    assert all(parameter in task for parameter in expected_parameters)
    assert f"dynamodb:{action}" in policy
    assert "var.workflow_dynamodb_table_0_arn" in policy
    assert "module.target-resource.table_name" in "\n".join(tree.values())
    assert "module.target-resource.table_arn" in "\n".join(tree.values())
    assert generate(payload) == tree


def test_multiple_tables_and_operations_are_scoped_independently():
    payload = architecture()
    payload["resources"][0]["config"]["definition"] = json.dumps(
        {
            "StartAt": "Read",
            "States": {
                "Read": {"Type": "Pass", "Next": "Write"},
                "Write": {"Type": "Pass", "End": True},
            },
        }
    )
    payload["connections"][0]["connection_config"] = {"state_name": "Read"}
    table = deepcopy(payload["resources"][1])
    table.update(id="second", name="z-table")
    table["config"]["table_name"] = "z-table"
    payload["resources"].append(table)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="z-table", target_id="second")
    connection["connection_config"] = {"state_name": "Write", "operation": "put_item"}
    payload["connections"].append(connection)
    tree = generate(payload)
    task = next(
        value for path, value in tree.items() if path.endswith("/dynamodb_tasks.tf")
    )
    policy = next(
        value
        for path, value in tree.items()
        if path.endswith("/dynamodb_tasks_policy.tf")
    )
    assert "var.workflow_dynamodb_table_0_name" in task
    assert "var.workflow_dynamodb_table_1_name" in task
    assert '"dynamodb:GetItem"' in policy
    assert '"dynamodb:PutItem"' in policy
    assert "var.workflow_dynamodb_table_0_arn" in policy
    assert "var.workflow_dynamodb_table_1_arn" in policy
    parsed = hcl2.loads(policy)
    expression = parsed["resource"][0]['"aws_iam_role_policy"']['"dynamodb_tasks"'][
        "policy"
    ]
    assert (
        'Action = ["dynamodb:GetItem"], Resource = [var.workflow_dynamodb_table_0_arn]'
        in expression
    )
    assert (
        'Action = ["dynamodb:PutItem"], Resource = [var.workflow_dynamodb_table_1_arn]'
        in expression
    )
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_invalid_operation_paths_and_expressions_rejected():
    invalid = [
        {"operation": "scan"},
        {"key_path": "$.orders[*]"},
        {"operation": "update_item"},
        {"operation": "put_item", "consistent_read": True},
        {"operation": "get_item", "condition_expression": "attribute_exists(id)"},
        {"operation": "update_item", "update_expression": "SET #n = :v"},
        {"operation": "put_item", "expression_attribute_values_path": "$.values"},
        {"operation": "put_item", "condition_expression": " "},
    ]
    for settings in invalid:
        with pytest.raises(ValidationError):
            StepFunctionsDynamoDbConfig.model_validate(settings)


@pytest.mark.parametrize("managed", [False, True])
def test_encrypted_tables_grant_scoped_decrypt(managed):
    payload = architecture()
    if managed:
        add_key(payload)
    else:
        payload["resources"][1]["config"].update(
            server_side_encryption_enabled=True,
            server_side_encryption_kms_key_arn="alias/external-key",
        )
    tree = generate(payload)
    policy = next(
        value
        for path, value in tree.items()
        if path.endswith("/dynamodb_tasks_policy.tf")
    )
    assert "kms:Decrypt" in policy
    if managed:
        assert "var.workflow_dynamodb_key_0_arn" in policy
        assert "module.encryption-key.key_arn" in "\n".join(tree.values())
    else:
        assert "data.aws_kms_key.workflow_dynamodb_key_0_arn.arn" in policy
        assert "module.target-resource.kms_access_key_id" in "\n".join(tree.values())


def test_external_key_without_table_encryption_rejected():
    payload = architecture()
    payload["resources"][1]["config"]["server_side_encryption_kms_key_arn"] = (
        "alias/external-key"
    )
    with pytest.raises(
        InvalidConnectionConfigError, match="requires server-side encryption"
    ):
        generate(payload)


def test_missing_role_placeholder_and_conflicting_state_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["role_arn"] = ""
    with pytest.raises(InvalidConnectionConfigError, match="execution role ARN"):
        generate(payload)
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"state_name": "Missing"}
    with pytest.raises(
        InvalidConnectionConfigError, match="existing top-level Pass state"
    ):
        generate(payload)
    payload = architecture()
    duplicate = deepcopy(payload["connections"][0])
    duplicate["connection_config"] = {"operation": "put_item"}
    payload["connections"].append(duplicate)
    with pytest.raises(InvalidConnectionConfigError, match="same workflow state"):
        generate(payload)


def test_sqs_and_dynamodb_states_compose_in_any_order():
    payload = sqs_architecture()
    payload["resources"][0]["config"]["definition"] = json.dumps(
        {
            "StartAt": "Queue",
            "States": {
                "Queue": {"Type": "Pass", "Next": "Lookup"},
                "Lookup": {"Type": "Pass", "End": True},
            },
        }
    )
    payload["connections"][0]["connection_config"] = {"state_name": "Queue"}
    table = deepcopy(architecture()["resources"][1])
    table.update(id="table", name="items")
    payload["resources"].append(table)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(
        source="source-resource", source_id="src", target="items", target_id="table"
    )
    connection["connection_config"] = {"state_name": "Lookup"}
    payload["connections"].append(connection)
    tree = generate(payload)
    machine = next(
        value for path, value in tree.items() if path.endswith("/step-functions.tf")
    )
    task = next(
        value for path, value in tree.items() if path.endswith("/dynamodb_tasks.tf")
    )
    assert "local.sqs_workflow_definition" in task
    assert "local.sqs_tasks_valid" in machine
    assert "local.dynamodb_tasks_valid" in machine
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_sqs_and_dynamodb_cannot_replace_the_same_state():
    payload = sqs_architecture()
    table = deepcopy(architecture()["resources"][1])
    table.update(id="table", name="items")
    payload["resources"].append(table)
    connection = deepcopy(architecture()["connections"][0])
    connection.update(
        source="source-resource", source_id="src", target="items", target_id="table"
    )
    payload["connections"].append(connection)
    with pytest.raises(InvalidConnectionConfigError, match="multiple task connections"):
        generate(payload)


def test_dynamodb_task_preserves_transition_and_data_path(tmp_path):
    if shutil.which("terraform") is None:
        pytest.skip("terraform binary not installed")
    definition = {
        "StartAt": "Lookup",
        "States": {
            "Lookup": {
                "Type": "Pass",
                "Next": "Done",
                "ResultPath": "$.item",
                "Result": "placeholder",
            },
            "Done": {"Type": "Succeed"},
        },
    }
    content = HCLRenderer().render_variable(
        "definition", "string", "Workflow", default=json.dumps(definition)
    )
    content += (
        dynamodb_workflow_locals(
            {
                "Lookup": {
                    "operation": "getItem",
                    "parameters": {"TableName": Expr('"items"'), "Key.$": "$.key"},
                }
            },
            False,
            False,
            False,
            False,
            False,
            False,
        )
        .replace('data "aws_partition" "dynamodb_tasks" {}\n', "")
        .replace("data.aws_partition.dynamodb_tasks.partition", '"aws"')
    )
    (tmp_path / "main.tf").write_text(content)
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input="jsonencode({valid = local.dynamodb_tasks_valid, workflow = jsondecode(local.dynamodb_workflow_definition)})\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(json.loads(result.stdout.strip()))
    assert output["valid"] is True
    state = output["workflow"]["States"]["Lookup"]
    assert state["Resource"] == "arn:aws:states:::dynamodb:getItem"
    assert state["Next"] == "Done"
    assert state["ResultPath"] == "$.item"
    assert "Result" not in state
    assert state["Parameters"]["Key.$"] == "$.key"


@needs_terraform
@pytest.mark.parametrize(
    "operation,encryption",
    [
        ("get_item", "none"),
        ("put_item", "none"),
        ("update_item", "none"),
        ("delete_item", "none"),
        ("get_item", "managed"),
        ("get_item", "external"),
    ],
)
def test_step_functions_dynamodb_validates(tmp_path, operation, encryption):
    payload = architecture()
    if encryption == "managed":
        add_key(payload)
    elif encryption == "external":
        payload["resources"][1]["config"].update(
            server_side_encryption_enabled=True,
            server_side_encryption_kms_key_arn="alias/external-key",
        )
    settings = {"operation": operation}
    if operation == "update_item":
        settings["update_expression"] = "REMOVE obsolete"
    payload["connections"][0]["connection_config"] = settings
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
