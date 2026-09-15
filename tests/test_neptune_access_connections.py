"""Neptune graph clients use scoped IAM actions and signed runtime connections."""

import json
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models import ArchitectureDescription, ServiceType
from app.models.input_models.neptune_config import NEPTUNE_DATA_AUTH_VERSION_PATTERN
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
    return connection_architecture(resolve_spec(source, ServiceType.NEPTUNE, kind, {}))


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


def generate(payload):
    return CodeGenerator().generate(project(payload))


@given(
    source=st.sampled_from([ServiceType.LAMBDA, ServiceType.ECS]),
    kind=st.sampled_from(["reads_from", "writes_to"]),
)
def test_graph_actions_and_runtime_metadata(source, kind):
    payload = architecture(source, kind)
    tree = generate(payload)
    policy = json.loads(
        tree["connection-check/iam-policies/source-resource-policy.json"]
    )
    grants = [
        s
        for s in policy["Statement"]
        if any(a.startswith("neptune-db:") for a in s["Action"])
    ]
    assert len(grants) == 1
    assert grants[0]["Resource"] == "${var.neptune_target-resource_data_arn}"
    assert set(grants[0]["Action"]) == (
        {"neptune-db:ReadDataViaQuery"}
        if kind == "reads_from"
        else {
            "neptune-db:ReadDataViaQuery",
            "neptune-db:WriteDataViaQuery",
            "neptune-db:DeleteDataViaQuery",
        }
    )
    text = "\n".join(tree.values())
    assert "iam_database_authentication_enabled = true" in text
    assert "aws_neptune_cluster.target-resource.cluster_resource_id" in text
    assert ":neptune-db:%s:%s:%s/*" in text
    for field in ["host", "reader_host", "port", "region"]:
        assert f"module.target-resource.graph_client_{field}" in text
        assert f'output "neptune_target-resource_{field}"' in text
    assert "postcondition {" in text and "self.engine_version" in text
    assert "neptune-db:connect" not in text
    assert "neptune-db:ResetDatabase" not in text
    assert "secretsmanager:GetSecretValue" not in text
    assert 'resource "aws_neptune_cluster_instance"' not in text
    if source == ServiceType.ECS:
        assert "task_role_arn = aws_iam_role.source-resource_role.arn" in text
    assert ConnectionPreviewer().preview_all(project(payload))[0].issues


@pytest.mark.parametrize(
    "version", ["1.0.5.1", "1.1.1.0", "0.9.0.0", "old", "", "1.10", "1.01.0.0"]
)
def test_unsupported_explicit_engines_are_rejected(version):
    payload = architecture()
    payload["resources"][1]["config"]["engine_version"] = version
    with pytest.raises(InvalidConnectionConfigError, match="1.2.0.0 or newer"):
        generate(payload)


@pytest.mark.parametrize(
    "version", ["1.2.0.0", "1.2.1.0.R6", "1.4.6.0", "1.10.0.0", "2.0.0.0", "10.0.0.0"]
)
def test_supported_explicit_versions_have_override_guards(version):
    payload = architecture()
    payload["resources"][1]["config"]["engine_version"] = version
    text = "\n".join(generate(payload).values())
    assert "engine_version = var.engine_version" in text
    assert "precondition {" in text
    assert "var.engine_version))" in text


def test_unconnected_cluster_does_not_enable_iam():
    payload = architecture()
    payload["connections"] = []
    text = "\n".join(generate(payload).values())
    assert "iam_database_authentication_enabled" not in text
    assert "postcondition" not in text


@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_duplicate_and_converging_access_is_deterministic(source):
    payload = architecture(source)
    write = deepcopy(payload["connections"][0])
    write["connection_type"] = "writes_to"
    payload["connections"].append(write)
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected
    assert (
        "\n".join(expected.values()).count("iam_database_authentication_enabled = true")
        == 1
    )


@needs_terraform
def test_neptune_resource_arn_and_version_guards_evaluate(tmp_path):
    ir = project(architecture())
    spec = resolve_spec(ServiceType.LAMBDA, ServiceType.NEPTUNE, "reads_from", {})
    result = spec.handler.handle(ir.connections[0], ir)
    arn = next(o.value for o in result.outputs if o.name == "graph_client_data_arn")
    arn = arn.replace(
        "aws_neptune_cluster.target-resource.arn",
        json.dumps(
            "arn:aws-us-gov:rds:us-gov-west-1:987654321098:cluster:display-name"
        ),
    )
    arn = arn.replace(
        "aws_neptune_cluster.target-resource.cluster_resource_id",
        json.dumps("cluster-IMMUTABLE"),
    )
    pattern = HCLRenderer().render_expression(NEPTUNE_DATA_AUTH_VERSION_PATTERN)
    expression = f'jsonencode({{ arn = {arn}, versions = [for v in ["1.1.1.0", "1.2.0.0", "1.10.0.0", "2.0.0.0"] : can(regex({pattern}, v))] }})'
    evaluated = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input=expression + "\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert evaluated.returncode == 0, evaluated.stderr
    assert json.loads(json.loads(evaluated.stdout)) == {
        "arn": "arn:aws-us-gov:neptune-db:us-gov-west-1:987654321098:cluster-IMMUTABLE/*",
        "versions": [False, True, True, True],
    }


@needs_terraform
@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_graph_access_validates_without_cycles(source, tmp_path):
    payload = architecture(source, "writes_to")
    payload["resources"][1]["config"]["engine_version"] = "1.4.6.0"
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
