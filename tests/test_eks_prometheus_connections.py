"""Managed collection validates native networking, scope, and AWS-owned access."""

import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.eks_prometheus import (
    scrape_configuration_expression,
    scraper_preconditions,
)
from app.models.connection_configs.eks_prometheus import EksPrometheusConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_grafana_prometheus_connections import console
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.EKS, ServiceType.MANAGED_PROMETHEUS, None, {})
    )


def connect_storage_and_grafana(payload):
    for source, target in (
        (ServiceType.EFS, ServiceType.EKS),
        (ServiceType.MANAGED_GRAFANA, ServiceType.MANAGED_PROMETHEUS),
    ):
        template = connection_architecture(resolve_spec(source, target, None, {}))
        name = source.value
        payload["resources"].append(dict(template["resources"][0], name=name, id=name))
        target_name = (
            "source-resource" if target == ServiceType.EKS else "target-resource"
        )
        target_id = "src" if target == ServiceType.EKS else "tgt"
        payload["connections"].append(
            dict(
                template["connections"][0],
                source=name,
                source_id=name,
                target=target_name,
                target_id=target_id,
            )
        )


def connect_managed_network(payload):
    payload["resources"][0]["config"]["subnet_ids"] = []
    template = connection_architecture(
        resolve_spec(ServiceType.VPC, ServiceType.SUBNET, None, {})
    )
    payload["resources"].append(
        dict(template["resources"][0], name="network", id="network")
    )
    placement = connection_architecture(
        resolve_spec(ServiceType.SUBNET, ServiceType.EKS, None, {})
    )["connections"][0]
    for index, zone in enumerate(["us-east-1a", "us-east-1b"]):
        name = f"subnet-{index}"
        subnet = deepcopy(template["resources"][1])
        subnet.update(name=name, id=name)
        subnet["config"].update(cidr_block=f"10.0.{index}.0/24", availability_zone=zone)
        payload["resources"].append(subnet)
        payload["connections"].extend(
            [
                dict(
                    template["connections"][0],
                    source="network",
                    source_id="network",
                    target=name,
                    target_id=name,
                ),
                dict(
                    placement,
                    source=name,
                    source_id=name,
                    target="source-resource",
                    target_id="src",
                ),
            ]
        )


def evaluate(tmp_path, expression, replacements):
    for name, value in replacements.items():
        expression = expression.replace(
            name, json.dumps(value).replace("${", "$${").replace("%{", "%%{")
        )
    (tmp_path / "payload.tf").write_text(f"locals {{\n  payload = {expression}\n}}\n")
    return json.loads(json.loads(console(tmp_path, "jsonencode(local.payload)")))


def native_values():
    return {
        "aws_eks_cluster.source": {
            "arn": "arn:aws:eks:us-east-1:123456789012:cluster/application",
            "access_config": [{"authentication_mode": "API_AND_CONFIG_MAP"}],
            "vpc_config": [
                {
                    "endpoint_private_access": True,
                    "subnet_ids": ["subnet-12345678", "subnet-87654321"],
                }
            ],
        },
        "data.aws_vpc.eks_prometheus.enable_dns_support": True,
        "data.aws_vpc.eks_prometheus.enable_dns_hostnames": True,
        "each.value.workspace_arn": "arn:aws:aps:us-east-1:123456789012:workspace/ws-12345678-abcd",
        "each.value.scrape_interval_seconds": 60,
    }


def test_native_scraper_ownership_and_aws_access_defaults():
    tree = generate(architecture())
    cluster = resources(tree, "aws_eks_cluster")[0]
    assert (
        cluster["access_config"][0]["authentication_mode"]
        == "${var.authentication_mode}"
    )
    assert (
        cluster["vpc_config"][0]["endpoint_private_access"]
        == "${var.endpoint_private_access}"
    )
    assert "endpoint_public_access" not in cluster["vpc_config"][0]
    scraper = resources(tree, "aws_prometheus_scraper")[0]
    native = "aws_eks_cluster.source-resource"
    source = scraper["source"][0]["eks"][0]
    expected_source = {
        "cluster_arn": "${" + native + ".arn}",
        "subnet_ids": "${" + native + ".vpc_config[0].subnet_ids}",
        "security_group_ids": [
            "${" + native + ".vpc_config[0].cluster_security_group_id}"
        ],
    }
    assert {key: source[key] for key in expected_source} == expected_source
    assert len(scraper["lifecycle"][0]["precondition"]) == 5
    assert "base64encode" not in scraper["scrape_configuration"]
    assert resources(tree, "aws_prometheus_workspace")[0]["tags"] == {
        "AMPAgentlessScraper": ""
    }
    for resource_type in (
        "aws_iam_role",
        "aws_iam_role_policy",
        "aws_eks_access_entry",
        "aws_eks_access_policy_association",
        "aws_security_group_rule",
    ):
        assert not resources(tree, resource_type)
    main = file_with(tree, "/environments/dev/main.tf")
    assert "module.target-resource.workspace_arn" in main
    variables = file_with(tree, "/source-resource/variables.tf")
    assert 'default     = "API_AND_CONFIG_MAP"' in variables
    assert "default     = true" in variables
    outputs = file_with(tree, "/source-resource/outputs.tf")
    assert 'output "prometheus_scrapers"' in outputs
    assert "scraper.role_arn" in outputs
    assert "scraper.destination[0].amp[0].workspace_arn" in outputs
    assert "source-resource" not in file_with(tree, "/target-resource/outputs.tf")


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=5, unique=True),
    interval=st.integers(30, 3600),
)
@settings(max_examples=25)
def test_bindings_are_deterministic_and_do_not_collide(names, interval):
    payload = architecture()
    target = payload["resources"].pop()
    connection = payload["connections"].pop()
    for name in names:
        payload["resources"].append(
            dict(deepcopy(target), name=f"metrics-{name}", id=name)
        )
        payload["connections"].append(
            dict(
                deepcopy(connection),
                target=f"metrics-{name}",
                target_id=name,
                connection_config={"scrape_interval_seconds": interval},
            )
        )
    tree = generate(payload)
    assert len(resources(tree, "aws_prometheus_workspace")) == len(names)
    main = file_with(tree, "/environments/dev/main.tf")
    for name in names:
        assert f"module.metrics-{name}.workspace_arn" in main
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


def test_conflicting_duplicate_intervals_are_rejected():
    payload = architecture()
    payload["connections"].append(
        dict(
            payload["connections"][0],
            connection_config={"scrape_interval_seconds": 120},
        )
    )
    with pytest.raises(InvalidConnectionConfigError, match="one scrape interval"):
        generate(payload)


@pytest.mark.parametrize("value", [0, 29, 3601, True, 60.5, "60"])
def test_typed_intervals_reject_invalid_values(value):
    with pytest.raises(ValidationError):
        EksPrometheusConfig(scrape_interval_seconds=value)


@pytest.mark.parametrize(
    "key,value",
    [("authentication_mode", "CONFIG_MAP"), ("endpoint_private_access", False)],
)
def test_explicit_incompatible_cluster_settings_are_rejected(key, value):
    payload = architecture()
    payload["resources"][0]["config"][key] = value
    with pytest.raises(InvalidConnectionConfigError, match=key):
        generate(payload)


@pytest.mark.parametrize("mode", ["API", "API_AND_CONFIG_MAP"])
def test_compatible_explicit_authentication_is_preserved(mode):
    payload = architecture()
    payload["resources"][0]["config"].update(
        authentication_mode=mode, endpoint_private_access=True
    )
    assert f'default     = "{mode}"' in file_with(
        generate(payload), "/source-resource/variables.tf"
    )


def test_unconnected_services_keep_existing_defaults():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    cluster = resources(tree, "aws_eks_cluster")[0]
    assert "access_config" not in cluster
    assert "endpoint_private_access" not in cluster["vpc_config"][0]
    assert "tags" not in resources(tree, "aws_prometheus_workspace")[0]
    assert not resources(tree, "aws_prometheus_scraper")


def test_shared_workspace_does_not_depend_on_scraper_sources():
    payload = architecture()
    payload["resources"].append(
        dict(deepcopy(payload["resources"][0]), name="other-cluster", id="other")
    )
    payload["connections"].append(
        dict(payload["connections"][0], source="other-cluster", source_id="other")
    )
    tree = generate(payload)
    assert len(resources(tree, "aws_prometheus_workspace")) == 1
    assert len(resources(tree, "aws_prometheus_scraper")) == 2
    assert not any(
        "other-cluster" in content
        for path, content in tree.items()
        if "/target-resource/" in path
    )


def test_preview_explains_authentication_lifecycle_and_external_prerequisites():
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    assert {item.module for item in preview.resources} == {"source-resource"}
    assert {item.resource_type for item in preview.resources} == {
        "aws_prometheus_scraper"
    }
    assert not preview.iam
    messages = " ".join(issue.message for issue in preview.issues)
    for text in (
        "cannot be reversed",
        "aws-auth",
        "service-linked role",
        "two to five",
        "networking",
        "billed scraper",
        "deduplication",
    ):
        assert text in messages


def test_explicit_cross_region_bindings_are_rejected():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "us-east-1"
    payload["resources"][1]["provider_region"] = "eu-west-1"
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)


@needs_terraform
@pytest.mark.parametrize(
    "mode,failed",
    [
        ("same", None),
        ("config_map", 0),
        ("public_only", 0),
        ("one_subnet", 1),
        ("six_subnets", 1),
        ("dns_support", 2),
        ("dns_hostnames", 2),
        ("cross_region", 3),
        ("cross_account", 3),
        ("cross_partition", 3),
        ("invalid_arn", 3),
        ("wildcard_arn", 3),
        ("low_interval", 4),
        ("high_interval", 4),
        ("fractional_interval", 4),
    ],
)
def test_native_guards_catch_terraform_override_mismatches(tmp_path, mode, failed):
    replacements = native_values()
    cluster = replacements["aws_eks_cluster.source"]
    if mode == "config_map":
        cluster["access_config"][0]["authentication_mode"] = "CONFIG_MAP"
    elif mode == "public_only":
        cluster["vpc_config"][0]["endpoint_private_access"] = False
    elif mode in {"one_subnet", "six_subnets"}:
        cluster["vpc_config"][0]["subnet_ids"] = [
            f"subnet-{index}" for index in range(1 if mode == "one_subnet" else 6)
        ]
    elif mode in {"dns_support", "dns_hostnames"}:
        replacements[f"data.aws_vpc.eks_prometheus.enable_{mode}"] = False
    elif mode in {
        "cross_region",
        "cross_account",
        "cross_partition",
        "invalid_arn",
        "wildcard_arn",
    }:
        arn = replacements["each.value.workspace_arn"]
        replacements["each.value.workspace_arn"] = {
            "cross_region": arn.replace("us-east-1", "eu-west-1"),
            "cross_account": arn.replace("123456789012", "999999999999"),
            "cross_partition": arn.replace("arn:aws:", "arn:aws-cn:"),
            "invalid_arn": "invalid",
            "wildcard_arn": arn.replace("ws-12345678-abcd", "ws-*"),
        }[mode]
    elif mode.endswith("interval"):
        replacements["each.value.scrape_interval_seconds"] = {
            "low_interval": 29,
            "high_interval": 3601,
            "fractional_interval": 60.5,
        }[mode]
    expression = (
        "["
        + ", ".join(
            str(item["condition"])
            for item in scraper_preconditions("aws_eks_cluster.source")
        )
        + "]"
    )
    assert evaluate(tmp_path, expression, replacements) == [
        index != failed for index in range(5)
    ]


@needs_terraform
@pytest.mark.parametrize("with_global", [False, True])
@given(interval=st.integers(30, 3600))
@settings(max_examples=5, deadline=None)
def test_default_jobs_and_other_global_settings_survive_interval_merge(
    with_global, interval
):
    defaults = {
        "scrape_configs": [
            {
                "job_name": "pods",
                "kubernetes_sd_configs": [{"role": "pod"}],
                "relabel_configs": [
                    {
                        "source_labels": [
                            "__meta_kubernetes_pod_annotation_prometheus_io_scrape"
                        ],
                        "regex": "true",
                        "action": "keep",
                    }
                ],
            }
        ]
    }
    if with_global:
        defaults["global"] = {
            "scrape_interval": "30s",
            "scrape_timeout": "10s",
            "external_labels": {"literal": "${value}"},
        }
    expression = (
        "yamldecode("
        + scrape_configuration_expression(
            "local.default_configuration", "local.interval"
        )
        + ")"
    )
    with TemporaryDirectory() as directory:
        actual = evaluate(
            Path(directory),
            expression,
            {
                "local.default_configuration": json.dumps(defaults),
                "local.interval": interval,
            },
        )
    expected = deepcopy(defaults)
    expected.setdefault("global", {})["scrape_interval"] = f"{interval}s"
    assert actual == expected


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode",
    [
        "plain",
        "multiple_workspaces",
        "shared_workspace",
        "mixed",
        "regional",
        "managed_network",
    ],
)
def test_generated_projects_validate_and_have_acyclic_graphs(tmp_path, mode):
    payload = architecture()
    if mode == "multiple_workspaces":
        payload["resources"].append(
            dict(deepcopy(payload["resources"][1]), name="other-workspace", id="other")
        )
        payload["connections"].append(
            dict(payload["connections"][0], target="other-workspace", target_id="other")
        )
    elif mode == "shared_workspace":
        payload["resources"].append(
            dict(deepcopy(payload["resources"][0]), name="other-cluster", id="other")
        )
        payload["connections"].append(
            dict(payload["connections"][0], source="other-cluster", source_id="other")
        )
    elif mode == "mixed":
        connect_storage_and_grafana(payload)
    elif mode == "regional":
        for item in payload["resources"]:
            item["provider_region"] = "eu-west-1"
    elif mode == "managed_network":
        connect_managed_network(payload)
    tree = generate(payload)
    if mode == "mixed":
        assert len(resources(tree, "aws_eks_addon")) == 1
        assert "efs_storage_manifests" in file_with(tree, "/source-resource/outputs.tf")
        assert len(resources(tree, "aws_grafana_workspace")) == 1
    if mode == "managed_network":
        main = file_with(tree, "/environments/dev/main.tf")
        assert (
            "subnet_ids = [module.subnet-0.subnet_id, module.subnet-1.subnet_id]"
            in main
        )
        payload["connections"] = list(reversed(payload["connections"]))
        assert generate(payload) == tree
    _write_tree(tmp_path, tree)
    path = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], path.parent
    )
    _run_terraform(["validate", "-no-color"], path.parent)
    _run_terraform(["graph", "-type=plan"], path.parent)
