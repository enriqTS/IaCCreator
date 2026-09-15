"""Standalone cache bindings preserve engine-specific endpoints and transport state."""

import json
import subprocess
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.elasticache_client import ElastiCacheClientHandler
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


def architecture(source=ServiceType.LAMBDA, engine="memcached", count=2):
    payload = connection_architecture(
        resolve_spec(source, ServiceType.ELASTICACHE, None, {})
    )
    payload["resources"][1]["config"].update(
        engine=engine,
        num_cache_nodes=1 if engine == "redis" else count,
        engine_version="7.1" if engine == "redis" else "1.6.22",
        parameter_group_name="default.redis7"
        if engine == "redis"
        else "default.memcached1.6",
    )
    return payload


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


def generate(payload):
    return CodeGenerator().generate(project(payload))


@given(
    source=st.sampled_from([ServiceType.LAMBDA, ServiceType.ECS]),
    engine=st.sampled_from(["redis", "memcached"]),
    count=st.integers(min_value=1, max_value=40),
)
def test_metadata_preserves_native_types_without_granting_iam(source, engine, count):
    payload = architecture(source, engine, count)
    ir = project(payload)
    contribution = ElastiCacheClientHandler().handle(ir.connections[0], ir)
    assert contribution.iam == []
    assert contribution.resources == []
    types = {item.name: item.type for item in contribution.inputs}
    assert (
        types["elasticache_target-resource_nodes"]
        == "list(object({ address = string, port = number }))"
    )
    assert types["elasticache_target-resource_tls"] == "bool"
    tree = generate(payload)
    text = "\n".join(tree.values())
    assert "engine = var.elasticache_target-resource_engine" in text
    assert "tls = var.elasticache_target-resource_tls" in text
    assert "aws_elasticache_cluster.target-resource.cache_nodes" in text
    assert "parameter_group_name = var.parameter_group_name" in text
    assert "engine_version = var.engine_version" in text
    assert "elasticache:Connect" not in text
    assert "aws_elasticache_replication_group" not in text
    payload["connections"] = []
    assert (
        tree["connection-check/iam-policies/source-resource-policy.json"]
        == generate(payload)[
            "connection-check/iam-policies/source-resource-policy.json"
        ]
    )
    assert any(
        "TLS" in issue.message
        for issue in ConnectionPreviewer().preview_all(ir)[0].issues
    )


@needs_terraform
@pytest.mark.parametrize(
    "engine,tls", [("memcached", False), ("memcached", True), ("redis", False)]
)
def test_terraform_evaluates_stable_nodes_discovery_and_actual_tls(
    engine, tls, tmp_path
):
    ir = project(architecture(engine=engine))
    contribution = ElastiCacheClientHandler().handle(ir.connections[0], ir)
    nodes = [
        {"id": "0002", "address": "second.cache", "port": 11211},
        {"id": "0001", "address": "first.cache", "port": 11212},
    ]
    if engine == "redis":
        nodes = [{"id": "0001", "address": "redis.cache", "port": 6379}]
    cluster = {
        "engine": engine,
        "transit_encryption_enabled": tls,
        "configuration_endpoint": "cluster.cfg.cache:11211"
        if engine == "memcached"
        else None,
        "cache_nodes": nodes,
    }
    literal = HCLRenderer().render_expression(json.dumps(cluster))
    expressions = {
        output.name: output.value.replace(
            "aws_elasticache_cluster.target-resource", f"jsondecode({literal})"
        )
        for output in contribution.outputs
        if output.module == "target-resource"
    }
    expression = (
        "{" + ", ".join(f"{key} = {value}" for key, value in expressions.items()) + "}"
    )
    result = subprocess.run(
        ["terraform", "console", "-no-color"],
        input=f"jsonencode({expression})\n",
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    values = json.loads(json.loads(result.stdout))
    assert values["client_tls"] is tls
    assert values["client_engine"] == engine
    assert values["client_configuration_endpoint"] == (
        "cluster.cfg.cache:11211" if engine == "memcached" else ""
    )
    assert values["client_nodes"] == [
        {"address": node["address"], "port": node["port"]}
        for node in sorted(nodes, key=lambda node: node["id"])
    ]


@pytest.mark.parametrize(
    "override",
    [
        {"engine": None},
        {"engine": "valkey"},
        {"engine": "redis", "num_cache_nodes": 2},
        {"num_cache_nodes": 0},
        {"num_cache_nodes": 41},
        {"num_cache_nodes": None},
        {"node_type": None},
        {"parameter_group_name": None},
    ],
)
def test_incompatible_or_incomplete_cluster_settings_are_rejected(override):
    payload = architecture()
    payload["resources"][1]["config"].update(override)
    with pytest.raises(InvalidConnectionConfigError, match="parameter group"):
        generate(payload)


@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_multiple_caches_and_duplicate_connections_are_deterministic(source):
    payload = architecture(source)
    cache = architecture(source, "redis")["resources"][1]
    cache.update(id="redis-cache", name="redis-cache")
    cache["config"]["cluster_id"] = "redis-cache"
    payload["resources"].append(cache)
    connection = deepcopy(payload["connections"][0])
    connection.update(target="redis-cache", target_id="redis-cache")
    payload["connections"].append(connection)
    tree = generate(payload)
    assert "elasticache_redis-cache_client" in "\n".join(tree.values())
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


def test_default_connection_has_no_credentials_or_iam_permission_selector():
    spec = resolve_spec(ServiceType.LAMBDA, ServiceType.ELASTICACHE, None, {})
    assert spec.connection_type == "connects_to"
    assert spec.config_model.get_field_schema() == []


def test_external_network_and_parameter_settings_are_preserved():
    payload = architecture()
    payload["resources"][1]["config"].update(
        subnet_group_name="existing-cache-subnets",
        security_group_ids=["sg-12345678", "sg-87654321"],
        parameter_group_name="custom-memcached",
    )
    tree = generate(payload)
    text = "\n".join(tree.values())
    assert "subnet_group_name = var.subnet_group_name" in text
    assert "security_group_ids = var.security_group_ids" in text
    assert "existing-cache-subnets" in text
    assert "custom-memcached" in text
    assert "sg-12345678" in text
    assert "sg-87654321" in text
    assert "aws_elasticache_subnet_group" not in text


def test_shared_cache_has_one_native_endpoint_output():
    payload = architecture()
    other = architecture(ServiceType.ECS)
    resource = other["resources"][0]
    resource.update(id="ecs-client", name="ecs-client")
    payload["resources"].append(resource)
    connection = other["connections"][0]
    connection.update(source="ecs-client", source_id="ecs-client")
    payload["connections"].append(connection)
    tree = generate(payload)
    assert "\n".join(tree.values()).count('output "client_nodes"') == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


@needs_terraform
@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
@pytest.mark.parametrize("engine", ["redis", "memcached"])
def test_cache_clients_validate_without_dependency_cycles(source, engine, tmp_path):
    _write_tree(tmp_path, generate(architecture(source, engine)))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
