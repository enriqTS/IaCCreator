"""OpenSearch grants distinguish search POSTs from document mutations."""

import fnmatch
import json
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.models.connection_configs.opensearch import OpenSearchIndexAccessConfig
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
    return connection_architecture(
        resolve_spec(source, ServiceType.OPENSEARCH, kind, {})
    )


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


def generate(payload):
    return CodeGenerator().generate(project(payload))


def statements(tree):
    policy = json.loads(
        tree["connection-check/iam-policies/source-resource-policy.json"]
    )
    grants = [
        s for s in policy["Statement"] if any(a.startswith("es:") for a in s["Action"])
    ]
    for grant in grants:
        if isinstance(grant["Resource"], str):
            grant["Resource"] = [grant["Resource"]]
    return grants


def allows(grants, method, path):
    resource = "${var.opensearch_target-resource_domain_arn}/" + path
    return any(
        "es:ESHttp" + method in grant["Action"]
        and any(fnmatch.fnmatchcase(resource, pattern) for pattern in grant["Resource"])
        for grant in grants
    )


@given(
    source=st.sampled_from([ServiceType.LAMBDA, ServiceType.ECS]),
    kind=st.sampled_from(["reads_from", "writes_to"]),
    index=st.from_regex(r"[a-z][a-z0-9_.-]{0,25}", fullmatch=True),
)
def test_only_index_document_operations_are_granted(source, kind, index):
    payload = architecture(source, kind)
    payload["connections"][0]["connection_config"]["index_name"] = index
    tree = generate(payload)
    grants = statements(tree)
    assert grants
    for grant in grants:
        assert all(
            arn.startswith(
                "${var.opensearch_target-resource_domain_arn}/" + index + "/"
            )
            for arn in grant["Resource"]
        )
    assert allows(grants, "Post", index + "/_search") == (kind == "reads_from")
    assert allows(grants, "Get", index + "/_doc/123") == (kind == "reads_from")
    assert allows(grants, "Post", index + "/_doc") == (kind == "writes_to")
    assert allows(grants, "Put", index + "/_doc/123") == (kind == "writes_to")
    assert allows(grants, "Delete", index + "/_doc/123") == (kind == "writes_to")
    for method in ["Get", "Head", "Put", "Post", "Delete"]:
        for path in [
            "_bulk",
            "_cluster/settings",
            index,
            index + "/_settings",
            index + "/_aliases",
            "different-index-" + index + "/_search",
        ]:
            assert not allows(grants, method, path)
    text = "\n".join(tree.values())
    assert '"rest.action.multi.allow_explicit_index" = "false"' in text
    assert "enforce_https = true" in text
    assert 'tls_security_policy = "Policy-Min-TLS-1-2-2019-07"' in text
    assert (
        'format("https://%s", aws_opensearch_domain.target-resource.endpoint)' in text
    )
    assert f'index_name = "{index}"' in text
    assert "region = var.opensearch_target-resource_region" in text
    assert "aws_opensearch_domain_policy" not in text
    assert "secretsmanager:GetSecretValue" not in text
    if source == ServiceType.ECS:
        assert "task_role_arn = aws_iam_role.source-resource_role.arn" in text
    assert ConnectionPreviewer().preview_all(project(payload))[0].issues


@pytest.mark.parametrize(
    "name",
    [
        "",
        "*",
        "logs-*",
        "a,b",
        "a/_search",
        "../other",
        "a:b",
        "UPPERCASE",
        ".",
        "_all",
        "a" * 256,
    ],
)
def test_index_name_rejects_path_and_wildcard_expansion(name):
    with pytest.raises(ValidationError):
        OpenSearchIndexAccessConfig(index_name=name)


@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_multiple_indexes_and_access_modes_aggregate_deterministically(source):
    payload = architecture(source)
    write = deepcopy(payload["connections"][0])
    write["connection_type"] = "writes_to"
    other = deepcopy(write)
    other["connection_config"]["index_name"] = "audit-records"
    payload["connections"].extend([write, other])
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == expected
    assert len(statements(expected)) == 8
    assert (
        "\n".join(expected.values()).count(
            '"rest.action.multi.allow_explicit_index" = "false"'
        )
        == 1
    )


def test_default_is_read_and_index_is_required():
    spec = resolve_spec(ServiceType.LAMBDA, ServiceType.OPENSEARCH, None, {})
    assert spec.connection_type == "reads_from"
    with pytest.raises(ValidationError):
        spec.config_model()
    assert spec.config_model.get_field_schema()[0].required


def test_unconnected_domain_configuration_is_unchanged():
    payload = architecture()
    payload["connections"] = []
    text = "\n".join(generate(payload).values())
    assert "allow_explicit_index" not in text
    assert "enforce_https" not in text


@needs_terraform
@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_index_connections_validate_without_cycles(source, tmp_path):
    payload = architecture(source)
    write = deepcopy(payload["connections"][0])
    write["connection_type"] = "writes_to"
    payload["connections"].append(write)
    _write_tree(tmp_path, generate(payload))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
