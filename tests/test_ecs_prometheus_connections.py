"""Task collection preserves application containers and native destination boundaries."""

import json
import os
import re
import subprocess
import time
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.ecs_prometheus import (
    COLLECTOR_IMAGE,
    COLLECTOR_NAME,
    collection_preconditions,
    collector_configuration_expression,
)
from app.models.connection_configs.ecs_prometheus import EcsPrometheusConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_eks_prometheus_connections import evaluate
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_grafana_prometheus_connections import native_workspace
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.ECS, ServiceType.MANAGED_PROMETHEUS, None, {})
    )


def replacements(workspaces=None, settings=None):
    return {
        "var.prometheus_collection_workspaces": workspaces
        if workspaces is not None
        else {"metrics": native_workspace()},
        "var.prometheus_collection": settings or EcsPrometheusConfig().model_dump(),
        "var.container_definitions": json.dumps(
            [{"name": "app", "image": "image", "cpu": 64, "memory": 256}]
        ),
        "var.ecs_cpu": "256",
        "var.ecs_memory": "512",
        "var.ecs_launch_type": "FARGATE",
        "var.subnet_ids": ["subnet-12345678"],
        "var.security_group_ids": ["sg-12345678"],
        "data.aws_partition.ecs_prometheus.partition": "aws",
        "data.aws_partition.ecs_prometheus.dns_suffix": "amazonaws.com",
        "data.aws_region.ecs_prometheus.region": "us-east-1",
        "data.aws_caller_identity.ecs_prometheus.account_id": "123456789012",
    }


def configuration(tmp_path, values):
    return yaml.safe_load(
        evaluate(tmp_path, str(collector_configuration_expression()), values)
    )


@needs_terraform
@pytest.mark.skipif(
    not os.environ.get("ADOT_COLLECTOR_BINARY"),
    reason="optional ADOT collector binary not configured",
)
@pytest.mark.parametrize("port", [0, 9090])
def test_pinned_collector_starts_with_emitted_environment_configuration(tmp_path, port):
    config = configuration(
        tmp_path,
        replacements(
            settings={
                "collection_interval_seconds": 60,
                "application_metrics_port": port,
            }
        ),
    )

    class MetadataHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            metadata = {
                "Cluster": "arn:aws:ecs:us-east-1:123456789012:cluster/application",
                "TaskARN": "arn:aws:ecs:us-east-1:123456789012:task/application/1234567890abcdef",
                "Family": "application",
                "Revision": "1",
                "LaunchType": "FARGATE",
                "AvailabilityZone": "us-east-1a",
                "Containers": [],
            }
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(metadata).encode())

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), MetadataHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}"
    for exporter in config["exporters"].values():
        exporter["endpoint"] = endpoint + "/api/v1/remote_write"
    log_path = tmp_path / "collector.log"
    try:
        with log_path.open("w") as output:
            process = subprocess.Popen(
                [
                    os.environ["ADOT_COLLECTOR_BINARY"],
                    "--config=env:AOT_CONFIG_CONTENT",
                ],
                env={
                    "AWS_ACCESS_KEY_ID": "offline-validation",
                    "AWS_SECRET_ACCESS_KEY": "offline-validation",
                    "AWS_EC2_METADATA_DISABLED": "true",
                    "ECS_CONTAINER_METADATA_URI_V4": endpoint + "/v4/container",
                    "AWS_EXECUTION_ENV": "AWS_ECS_FARGATE",
                    "RUN_IN_CONTAINER": "True",
                    "AOT_CONFIG_CONTENT": yaml.safe_dump(config),
                },
                cwd=tmp_path,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if (
                        "Everything is ready" in log_path.read_text()
                        or process.poll() is not None
                    ):
                        break
                    time.sleep(0.05)
                assert "Everything is ready" in log_path.read_text(), (
                    log_path.read_text()
                )
            finally:
                process.terminate()
                process.wait(timeout=10)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def task(tree):
    return resources(tree, "aws_ecs_task_definition")[0]


def mixed_architecture():
    payload = architecture()
    for source, target in (
        (ServiceType.EFS, ServiceType.ECS),
        (ServiceType.ECS, ServiceType.SECRETS_MANAGER),
        (ServiceType.MANAGED_GRAFANA, ServiceType.MANAGED_PROMETHEUS),
    ):
        template = connection_architecture(resolve_spec(source, target, None, {}))
        peer_is_source = source != ServiceType.ECS
        peer = deepcopy(template["resources"][0 if peer_is_source else 1])
        name = peer["service_type"]
        peer.update(name=name, id=name)
        payload["resources"].append(peer)
        binding = deepcopy(template["connections"][0])
        if peer_is_source:
            target_name = (
                "source-resource" if target == ServiceType.ECS else "target-resource"
            )
            target_id = "src" if target == ServiceType.ECS else "tgt"
            binding.update(
                source=name, source_id=name, target=target_name, target_id=target_id
            )
        else:
            binding.update(
                source="source-resource", source_id="src", target=name, target_id=name
            )
        payload["connections"].append(binding)
    return payload


def test_native_destinations_and_existing_role_ownership():
    tree = generate(architecture())
    definition = task(tree)
    assert definition["task_role_arn"] == "${aws_iam_role.source-resource_role.arn}"
    assert definition["execution_role_arn"] == definition["task_role_arn"]
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_iam_role_policy")) == 1
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    assert len(definition["lifecycle"][0]["precondition"]) == 7
    assert not resources(tree, "aws_prometheus_scraper")
    assert "tags" not in resources(tree, "aws_prometheus_workspace")[0]
    assert resources(tree, "aws_ecs_service")[0]["platform_version"] == "LATEST"
    assert COLLECTOR_IMAGE in definition["container_definitions"]
    assert "--config=env:AOT_CONFIG_CONTENT" in definition["container_definitions"]
    main = file_with(tree, "/environments/dev/main.tf")
    for output in (
        "workspace_arn",
        "prometheus_endpoint",
        "iam_aws_prometheus_workspace_arn",
    ):
        assert f"module.target-resource.{output}" in main
    policy = json.loads(
        next(
            content
            for path, content in tree.items()
            if path.endswith("source-resource-policy.json")
        )
    )
    write = [
        item for item in policy["Statement"] if item["Action"] == ["aps:RemoteWrite"]
    ]
    assert (
        len(write) == 1
        and write[0]["Resource"] == "${aws_prometheus_workspace.target-resource.arn}"
    )
    assert not any("aps:QueryMetrics" in item["Action"] for item in policy["Statement"])
    assert "source-resource" not in file_with(tree, "/target-resource/outputs.tf")


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=4, unique=True),
    interval=st.integers(10, 3600),
    port=st.integers(0, 65535),
)
@settings(max_examples=20)
def test_one_collector_aggregates_destinations_and_duplicate_order(
    names, interval, port
):
    payload = architecture()
    destination = payload["resources"].pop()
    connection = payload["connections"].pop()
    for name in names:
        payload["resources"].append(
            dict(deepcopy(destination), name=f"metrics-{name}", id=name)
        )
        payload["connections"].append(
            dict(
                deepcopy(connection),
                target=f"metrics-{name}",
                target_id=name,
                connection_config={
                    "collection_interval_seconds": interval,
                    "application_metrics_port": port,
                },
            )
        )
    tree = generate(payload)
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    assert len(resources(tree, "aws_ecs_task_definition")) == 1
    assert len(resources(tree, "aws_iam_role")) == 1
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "field,value",
    [("collection_interval_seconds", 120), ("application_metrics_port", 9090)],
)
def test_conflicting_collection_settings_are_rejected(field, value):
    payload = architecture()
    payload["connections"].append(
        dict(payload["connections"][0], connection_config={field: value})
    )
    with pytest.raises(InvalidConnectionConfigError, match="must share"):
        generate(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("collection_interval_seconds", 9),
        ("collection_interval_seconds", 3601),
        ("collection_interval_seconds", 30.5),
        ("collection_interval_seconds", True),
        ("application_metrics_port", -1),
        ("application_metrics_port", 65536),
        ("application_metrics_port", 9090.5),
        ("application_metrics_port", "9090"),
    ],
)
def test_typed_settings_reject_unsafe_values(field, value):
    with pytest.raises(ValidationError):
        EcsPrometheusConfig(**{field: value})


@pytest.mark.parametrize("field", ["subnet_ids", "security_group_ids"])
def test_missing_task_placement_is_rejected(field):
    payload = architecture()
    payload["resources"][0]["config"][field] = []
    with pytest.raises(InvalidConnectionConfigError, match=field):
        generate(payload)


@pytest.mark.parametrize("launch", ["EC2", "EXTERNAL"])
def test_unmodeled_task_launch_types_are_rejected(launch):
    payload = architecture()
    payload["resources"][0]["config"]["ecs_launch_type"] = launch
    with pytest.raises(InvalidConnectionConfigError, match="Linux Fargate"):
        generate(payload)


def test_unconnected_tasks_keep_existing_rendering():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    assert task(tree)["container_definitions"] == "${var.container_definitions}"
    assert "task_role_arn" not in task(tree)
    assert "execution_role_arn" not in task(tree)
    assert not resources(tree, "aws_cloudwatch_log_group")


def test_preview_explains_collection_scope_and_runtime_requirements():
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    assert {item.resource_type for item in preview.resources} == {
        "aws_cloudwatch_log_group"
    }
    assert {item.module for item in preview.resources} == {"source-resource"}
    assert preview.iam[0].actions == ["aps:RemoteWrite"]
    for text in (
        "nonessential",
        "metadata-v4",
        "64 CPU",
        "256 MiB",
        "localhost",
        "share the task role",
        "cardinality",
        "outbound access",
    ):
        assert text in preview.issues[0].message


def test_explicit_cross_region_connections_are_rejected():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "us-east-1"
    payload["resources"][1]["provider_region"] = "eu-west-1"
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)


@needs_terraform
@given(
    interval=st.integers(10, 3600), port=st.integers(0, 65535), count=st.integers(1, 3)
)
@settings(max_examples=8, deadline=None)
def test_configuration_uses_metadata_and_optional_app_scraping_with_native_sigv4(
    interval, port, count
):
    workspaces = {f"metrics-{index}": native_workspace() for index in range(count)}
    for index, value in enumerate(workspaces.values()):
        value["arn"] += str(index)
        value["endpoint"] = value["endpoint"].rstrip("/") + str(index)
    values = replacements(
        workspaces,
        {"collection_interval_seconds": interval, "application_metrics_port": port},
    )
    with TemporaryDirectory() as directory:
        config = configuration(Path(directory), values)
    assert config["extensions"] == {
        "sigv4auth": {"region": "us-east-1", "service": "aps"}
    }
    assert (
        config["receivers"]["awsecscontainermetrics"]["collection_interval"]
        == f"{interval}s"
    )
    pipeline = config["service"]["pipelines"]["metrics"]
    assert pipeline["receivers"] == ["awsecscontainermetrics"] + (
        ["prometheus"] if port else []
    )
    assert set(pipeline["exporters"]) == set(config["exporters"])
    for key, value in workspaces.items():
        exporter = config["exporters"][f"prometheus_remote_write/{key}"]
        assert exporter == {
            "endpoint": value["endpoint"] + "/api/v1/remote_write",
            "auth": {"authenticator": "sigv4auth"},
            "resource_to_telemetry_conversion": {"enabled": True},
        }
    if port:
        scrape = config["receivers"]["prometheus"]["config"]
        assert scrape["global"]["scrape_interval"] == f"{interval}s"
        assert scrape["scrape_configs"][0]["static_configs"][0]["targets"] == [
            f"127.0.0.1:{port}"
        ]
        assert scrape["scrape_configs"][0]["metrics_path"] == "/metrics"
    assert config["processors"]["resource_detection"]["detectors"] == ["ecs"]
    assert "awsemf" not in config["exporters"]


@needs_terraform
@pytest.mark.parametrize(
    "mode,failed",
    [
        ("same", None),
        ("empty", 0),
        ("invalid_arn", 0),
        ("cross_account", 1),
        ("cross_partition", 1),
        ("cross_region", 1),
        ("bad_region_metadata", 1),
        ("bad_endpoint", 2),
        ("low_interval", 3),
        ("fractional_interval", 3),
        ("bad_port", 3),
        ("reserved_container", 4),
        ("empty_containers", 4),
        ("insufficient_cpu", 5),
        ("insufficient_memory", 5),
        ("launch", 6),
        ("subnets", 6),
        ("security_groups", 6),
    ],
)
def test_native_guards_reject_terraform_override_mismatches(tmp_path, mode, failed):
    values = replacements()
    workspace = values["var.prometheus_collection_workspaces"]["metrics"]
    if mode == "empty":
        values["var.prometheus_collection_workspaces"] = {}
    elif mode == "invalid_arn":
        workspace["arn"] = "invalid"
        workspace["endpoint"] = "invalid"
        workspace["region"] = "invalid"
    elif mode in {"cross_account", "cross_partition", "cross_region"}:
        updated = native_workspace(
            account="999999999999" if mode == "cross_account" else "123456789012",
            partition="aws-cn" if mode == "cross_partition" else "aws",
            region="eu-west-1" if mode == "cross_region" else "us-east-1",
        )
        workspace.update(updated)
    elif mode == "bad_region_metadata":
        workspace["region"] = "eu-west-1"
    elif mode == "bad_endpoint":
        workspace["endpoint"] = "https://attacker.example/workspaces/other"
    elif mode == "low_interval":
        values["var.prometheus_collection"]["collection_interval_seconds"] = 9
    elif mode == "fractional_interval":
        values["var.prometheus_collection"]["collection_interval_seconds"] = 60.5
    elif mode == "bad_port":
        values["var.prometheus_collection"]["application_metrics_port"] = 65536
    elif mode == "reserved_container":
        values["var.container_definitions"] = json.dumps([{"name": COLLECTOR_NAME}])
    elif mode == "empty_containers":
        values["var.container_definitions"] = "[]"
    elif mode == "insufficient_cpu":
        values["var.ecs_cpu"] = "64"
    elif mode == "insufficient_memory":
        values["var.ecs_memory"] = "256"
    elif mode == "launch":
        values["var.ecs_launch_type"] = "EC2"
    elif mode == "subnets":
        values["var.subnet_ids"] = []
    elif mode == "security_groups":
        values["var.security_group_ids"] = []
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in collection_preconditions())
        + "]"
    )
    expected = [index != failed for index in range(7)]
    if mode == "invalid_arn":
        expected[1] = expected[2] = False
    if mode == "bad_region_metadata":
        expected[2] = False
    assert evaluate(tmp_path, expression, values) == expected


@needs_terraform
@pytest.mark.parametrize("mixed", [False, True])
def test_serialized_task_preserves_application_configuration_and_adds_one_sidecar(
    tmp_path, mixed
):
    payload = mixed_architecture() if mixed else architecture()
    tree = generate(payload)
    content = next(
        content
        for content in tree.values()
        if 'resource "aws_ecs_task_definition"' in content
    )
    expression = re.search(
        r"\n  container_definitions = (.*?)\n  cpu = var\.ecs_cpu", content, re.S
    ).group(1)
    values = replacements()
    containers = [
        {
            "name": "source-resource",
            "image": "application",
            "cpu": 64,
            "memory": 256,
            "environment": [{"name": "KEEP", "value": "${literal}"}],
            "secrets": [{"name": "OLD", "valueFrom": "external"}],
            "mountPoints": [
                {
                    "sourceVolume": "external",
                    "containerPath": "/other",
                    "readOnly": False,
                }
            ],
        }
    ]
    values.update(
        {
            "var.container_definitions": json.dumps(containers),
            "local.prometheus_collector_configuration": json.dumps(
                configuration(tmp_path, replacements())
            ),
            "aws_cloudwatch_log_group.source-resource_prometheus.name": "/aws/ecs/source-resource/prometheus",
        }
    )
    if mixed:
        values["local.runtime_secrets"] = [
            {
                "container": "source-resource",
                "name": "SECRET_SECRETS_MANAGER",
                "valueFrom": "managed-secret",
            }
        ]
        values["local.efs_mounts"] = [
            {
                "container": "source-resource",
                "name": "managed-efs",
                "path": "/mnt/efs",
                "read_only": False,
            }
        ]
    result = json.loads(evaluate(tmp_path, expression, values))
    application, collector = result
    assert application["environment"] == containers[0]["environment"]
    assert application["mountPoints"][0] == containers[0]["mountPoints"][0]
    assert application["secrets"][0] == containers[0]["secrets"][0]
    if mixed:
        assert application["mountPoints"][1]["sourceVolume"] == "managed-efs"
        assert application["secrets"][1]["valueFrom"] == "managed-secret"
    else:
        assert application == containers[0]
    assert collector["name"] == COLLECTOR_NAME
    assert collector["image"] == COLLECTOR_IMAGE
    assert collector["essential"] is False
    assert collector["command"] == ["--config=env:AOT_CONFIG_CONTENT"]
    assert collector["memory"] == 256 and collector["cpu"] == 64
    assert not collector.get("portMappings")
    assert (
        collector["logConfiguration"]["options"]["awslogs-group"]
        == "/aws/ecs/source-resource/prometheus"
    )


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode",
    [
        "plain",
        "application",
        "multiple_destinations",
        "shared_workspace",
        "mixed",
        "regional",
        "managed_network",
        "shared_ingestion",
    ],
)
def test_projects_validate_and_have_acyclic_task_graphs(tmp_path, mode):
    payload = mixed_architecture() if mode == "mixed" else architecture()
    if mode == "application":
        payload["connections"][0]["connection_config"] = {
            "application_metrics_port": 9090
        }
    elif mode == "multiple_destinations":
        payload["resources"].append(
            dict(deepcopy(payload["resources"][1]), name="other-workspace", id="other")
        )
        payload["connections"].append(
            dict(payload["connections"][0], target="other-workspace", target_id="other")
        )
    elif mode == "shared_workspace":
        source = deepcopy(payload["resources"][0])
        source.update(name="other-task", id="other")
        source["config"].update(cluster_name="other-task", task_family="other-task")
        payload["resources"].append(source)
        payload["connections"].append(
            dict(payload["connections"][0], source="other-task", source_id="other")
        )
    elif mode == "regional":
        for item in payload["resources"]:
            item["provider_region"] = "eu-west-1"
    elif mode == "managed_network":
        for service, field in (
            (ServiceType.SUBNET, "subnet_ids"),
            (ServiceType.SECURITY_GROUP, "security_group_ids"),
        ):
            payload["resources"][0]["config"][field] = []
            template = connection_architecture(
                resolve_spec(service, ServiceType.ECS, None, {})
            )
            peer = deepcopy(template["resources"][0])
            peer.update(name=service.value, id=service.value)
            peer["config"]["vpc_id"] = "vpc-12345678"
            payload["resources"].append(peer)
            payload["connections"].append(
                dict(
                    template["connections"][0],
                    source=service.value,
                    source_id=service.value,
                    target="source-resource",
                    target_id="src",
                )
            )
    elif mode == "shared_ingestion":
        template = connection_architecture(
            resolve_spec(ServiceType.EKS, ServiceType.MANAGED_PROMETHEUS, None, {})
        )
        payload["resources"].append(
            dict(template["resources"][0], name="cluster", id="cluster")
        )
        payload["connections"].append(
            dict(
                template["connections"][0],
                source="cluster",
                source_id="cluster",
                target="target-resource",
                target_id="tgt",
            )
        )
    tree = generate(payload)
    if mode in {"mixed", "managed_network", "shared_ingestion"}:
        payload["connections"] = list(reversed(payload["connections"] * 2))
        assert generate(payload) == tree
    if mode == "managed_network":
        main = file_with(tree, "/environments/dev/main.tf")
        assert "module.subnet.subnet_id" in main
        assert "module.security-group.security_group_id" in main
    if mode == "shared_ingestion":
        assert len(resources(tree, "aws_prometheus_workspace")) == 1
        assert len(resources(tree, "aws_prometheus_scraper")) == 1
        assert resources(tree, "aws_prometheus_workspace")[0]["tags"] == {
            "AMPAgentlessScraper": ""
        }
    _write_tree(tmp_path, tree)
    path = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], path.parent
    )
    _run_terraform(["validate", "-no-color"], path.parent)
    _run_terraform(["graph", "-type=plan"], path.parent)
