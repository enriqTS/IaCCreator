"""Memcached TLS validates deployment prerequisites and preserves client metadata."""

import json
import subprocess

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.generators.elasticache_tls import tls_preconditions
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models import ServiceType
from app.models.input_models.elasticache_config import ElastiCacheConfig
from tests.test_elasticache_client_connections import architecture, generate
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)


def tls_architecture(source=ServiceType.LAMBDA):
    payload = architecture(source)
    payload["resources"][1]["config"].update(
        transit_encryption_enabled=True,
        engine_version="1.6.12",
        node_type="cache.t3.micro",
        subnet_group_name="cache-private",
        security_group_ids=["sg-cache"],
    )
    return payload


@given(
    source=st.sampled_from([ServiceType.LAMBDA, ServiceType.ECS]),
    patch=st.integers(min_value=12, max_value=999),
)
def test_tls_provisioning_retains_native_client_state_and_no_credentials(source, patch):
    payload = tls_architecture(source)
    payload["resources"][1]["config"]["engine_version"] = f"1.6.{patch}"
    tree = generate(payload)
    text = "\n".join(tree.values())
    assert "transit_encryption_enabled = var.transit_encryption_enabled" in text
    assert (
        "coalesce(aws_elasticache_cluster.target-resource.transit_encryption_enabled, false)"
        in text
    )
    assert "tls = var.elasticache_target-resource_tls" in text
    assert "Cache clients require standalone Redis" in text
    assert "Standalone cache TLS requires Memcached" in text
    assert "Memcached TLS requires VPC placement" in text
    assert "elasticache:Connect" not in text
    assert "auth_token" not in text
    assert "password" not in text
    payload["connections"] = []
    assert "transit_encryption_enabled = var.transit_encryption_enabled" in "\n".join(
        generate(payload).values()
    )


@pytest.mark.parametrize(
    "override",
    [
        {"engine": "redis"},
        {"engine": None},
        {"engine_version": None},
        {"engine_version": "1.6.11"},
        {"engine_version": "1.5.99"},
        {"engine_version": "1.6.12x"},
        {"engine_version": "1.6"},
        {"engine_version": "0.9.99"},
        {"subnet_group_name": None},
        {"subnet_group_name": " "},
        {"node_type": None},
        {"node_type": "cache.m1.small"},
        {"node_type": "cache.m2.xlarge"},
        {"node_type": "cache.m3.medium"},
        {"node_type": "cache.r3.large"},
        {"node_type": "cache.t2.micro"},
        {"node_type": "garbage"},
    ],
)
def test_invalid_tls_prerequisites_are_rejected(override):
    config = tls_architecture()["resources"][1]["config"]
    config.update(override)
    with pytest.raises(ValidationError, match="TLS"):
        ElastiCacheConfig.model_validate(config)


def test_default_false_preserves_unencrypted_cluster_generation():
    payload = architecture()
    expected = generate(payload)
    payload["resources"][1]["config"]["transit_encryption_enabled"] = False
    assert generate(payload) == expected
    assert "transit_encryption_enabled = var." not in "\n".join(expected.values())


@needs_terraform
@pytest.mark.parametrize(
    "override,allowed",
    [
        ({}, True),
        ({"engine_version": "1.6.11"}, False),
        ({"engine_version": "1.6.120"}, True),
        ({"engine_version": "1.7.0"}, True),
        ({"engine_version": "2.0.0"}, True),
        ({"engine_version": "1.6.12oops"}, False),
        ({"engine": "redis"}, False),
        ({"node_type": "cache.t2.micro"}, False),
        ({"subnet_group_name": ""}, False),
        ({"node_type": "invalid"}, False),
        ({"transit_encryption_enabled": False, "engine": "redis"}, True),
    ],
)
def test_terraform_tls_guards_evaluate_overrides(override, allowed, tmp_path):
    values = dict(
        transit_encryption_enabled=True,
        engine="memcached",
        engine_version="1.6.12",
        subnet_group_name="private",
        node_type="cache.t3.micro",
    )
    values.update(override)
    expressions = []
    for guard in tls_preconditions():
        expression = str(guard["condition"])
        for key in sorted(values, key=len, reverse=True):
            value = values[key]
            expression = expression.replace(
                f"var.{key}", HCLRenderer().render_expression(value)
            )
        expressions.append(expression)
    result = subprocess.run(
        ["terraform", "console", "-no-color"],
        cwd=tmp_path,
        input="alltrue([" + ", ".join(expressions) + "])\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) is allowed


@needs_terraform
@pytest.mark.parametrize("source", [ServiceType.LAMBDA, ServiceType.ECS])
def test_tls_client_projects_validate_without_cycles(source, tmp_path):
    _write_tree(tmp_path, generate(tls_architecture(source)))
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
