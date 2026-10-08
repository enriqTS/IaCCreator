"""Task-local tracing preserves application configuration and shared group identity."""

import json
import re
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.ecs_collector import COLLECTOR_IMAGE
from app.generators.ecs_xray import (
    COLLECTOR_NAME,
    TRACE_ENVIRONMENT,
    xray_configuration_expression,
    xray_task_preconditions,
)
from app.generators.xray_ecs_filters import ecs_group_preconditions, ecs_group_selectors
from app.generators.xray_filters import group_filter_expression, lambda_group_selectors
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_ecs_prometheus_connections import (
    mixed_architecture as metrics_architecture,
)
from tests.test_eks_prometheus_connections import evaluate
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate, project
from tests.test_lambda_xray_connections import native_values as lambda_values


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.ECS, ServiceType.X_RAY, None, {})
    )


def bind_lambda(payload, target="target-resource", target_id="tgt"):
    template = connection_architecture(
        resolve_spec(ServiceType.LAMBDA, ServiceType.X_RAY, None, {})
    )
    payload["resources"].append(
        dict(template["resources"][0], name="function", id="function")
    )
    payload["connections"].append(
        dict(
            template["connections"][0],
            source="function",
            source_id="function",
            target=target,
            target_id=target_id,
        )
    )


def mixed_architecture():
    payload = metrics_architecture()
    template = architecture()
    payload["resources"].append(
        dict(template["resources"][1], name="traces", id="traces")
    )
    payload["connections"].append(
        dict(template["connections"][0], target="traces", target_id="traces")
    )
    bind_lambda(payload, "traces", "traces")
    grafana = connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.X_RAY, None, {})
    )
    payload["connections"].append(
        dict(
            grafana["connections"][0],
            source="managed-grafana",
            source_id="managed-grafana",
            target="traces",
            target_id="traces",
        )
    )
    return payload


def native_values(*, prometheus=False):
    return {
        "aws_ecs_cluster.source-resource.arn": "arn:aws:ecs:us-east-1:123456789012:cluster/application",
        "data.aws_region.ecs_xray.region": "us-east-1",
        "var.container_definitions": json.dumps(
            [
                {
                    "name": "source-resource",
                    "image": "application",
                    "cpu": 64,
                    "memory": 256,
                }
            ]
        ),
        "var.ecs_cpu": "256",
        "var.ecs_memory": "1024" if prometheus else "512",
        "var.ecs_launch_type": "FARGATE",
        "var.subnet_ids": ["subnet-12345678"],
        "var.security_group_ids": ["sg-12345678"],
        "var.prometheus_collection.application_metrics_port": 9090,
    }


def native_group_values():
    values = lambda_values()
    values["var.xray_ecs_clusters"] = {
        "diagram-node": {
            "arn": "arn:aws:ecs:us-east-1:123456789012:cluster/application",
            "name": "application",
        }
    }
    return values


def configuration(tmp_path, values=None):
    return yaml.safe_load(
        evaluate(
            tmp_path,
            xray_configuration_expression("source-resource"),
            values or native_values(),
        )
    )


def test_native_group_identity_and_source_role_ownership():
    tree = generate(architecture())
    task = resources(tree, "aws_ecs_task_definition")[0]
    assert (
        task["task_role_arn"]
        == task["execution_role_arn"]
        == "${aws_iam_role.source-resource_role.arn}"
    )
    assert "${aws_iam_role_policy.source-resource_xray}" in task["depends_on"]
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_iam_role_policy")) == 2
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    assert len(task["lifecycle"][0]["precondition"]) == 5
    assert resources(tree, "aws_ecs_service")[0]["platform_version"] == "LATEST"
    assert COLLECTOR_NAME in task["container_definitions"]
    main = file_with(tree, "/environments/dev/main.tf")
    assert "module.source-resource.cluster_arn" in main
    assert "module.source-resource.xray_cluster_name" in main
    assert "module.target-resource.group_arn" not in main
    assert "module.target-resource" not in file_with(
        tree, "/source-resource/xray_collection.tf"
    )
    assert "aws_ecs_cluster.source-resource.name" in file_with(
        tree, "/source-resource/outputs.tf"
    )
    assert "aws_ecs_service.source-resource_service.name" not in file_with(
        tree, "/source-resource/xray_collection.tf"
    )


@given(
    names=st.lists(resource_name_st, min_size=1, max_size=4, unique=True),
    duplicate=st.booleans(),
)
@settings(max_examples=20)
def test_one_upload_per_task_with_multiple_groups_and_duplicates(names, duplicate):
    payload = architecture()
    target = payload["resources"].pop()
    connection = payload["connections"].pop()
    for name in names:
        group = deepcopy(target)
        group.update(name=f"group-{name}", id=f"group-{name}")
        group["config"]["group_name"] = f"g-{name}"
        payload["resources"].append(group)
        payload["connections"].append(
            dict(connection, target=f"group-{name}", target_id=f"group-{name}")
        )
    if duplicate:
        payload["connections"].append(deepcopy(payload["connections"][0]))
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role_policy")) == 2
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    assert len(resources(tree, "aws_xray_group")) == len(names)
    assert (
        resources(tree, "aws_ecs_task_definition")[0]["container_definitions"].count(
            COLLECTOR_NAME
        )
        == 1
    )
    payload["connections"].reverse()
    assert generate(payload) == tree


def test_shared_group_supports_multiple_ecs_tasks_and_lambda():
    payload = architecture()
    source = deepcopy(payload["resources"][0])
    source.update(name="other-task", id="other-task")
    source["config"].update(cluster_name="OtherCluster", task_family="OtherTask")
    payload["resources"].append(source)
    payload["connections"].append(
        dict(payload["connections"][0], source="other-task", source_id="other-task")
    )
    bind_lambda(payload)
    tree = generate(payload)
    assert len(resources(tree, "aws_xray_group")) == 1
    assert len(resources(tree, "aws_iam_role_policy")) == 6
    assert (
        len(resources(tree, "aws_xray_group")[0]["lifecycle"][0]["precondition"]) == 6
    )
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree


@pytest.mark.parametrize(
    "field,value",
    [("subnet_ids", []), ("security_group_ids", []), ("ecs_launch_type", "EC2")],
)
def test_unsupported_launch_and_missing_placement_are_rejected(field, value):
    payload = architecture()
    payload["resources"][0]["config"][field] = value
    for operation in [
        generate,
        lambda value: ConnectionPreviewer().preview_all(project(value)),
    ]:
        with pytest.raises(InvalidConnectionConfigError, match=field):
            operation(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("group_name", "Default"),
        ("group_name", "bad*group"),
        ("filter_expression", " "),
        ("notifications_enabled", True),
    ],
)
def test_invalid_group_configuration_is_rejected(field, value):
    payload = architecture()
    payload["resources"][1]["config"][field] = value
    with pytest.raises(InvalidConnectionConfigError, match=field):
        generate(payload)


def test_incompatible_metrics_ports_are_rejected_independent_of_connection_order():
    payload = mixed_architecture()
    payload["connections"][0]["connection_config"] = {"application_metrics_port": 4318}
    for _ in range(2):
        with pytest.raises(
            InvalidConnectionConfigError, match="application_metrics_port"
        ):
            generate(payload)
        payload["connections"].reverse()


def test_explicit_cross_region_binding_is_rejected():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "us-east-1"
    payload["resources"][1]["provider_region"] = "eu-west-1"
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)


def test_standalone_task_does_not_receive_tracing_changes():
    payload = architecture()
    payload["connections"] = []
    tree = generate(payload)
    task = resources(tree, "aws_ecs_task_definition")[0]
    assert task["container_definitions"] == "${var.container_definitions}"
    assert not any(path.endswith("/xray_collection.tf") for path in tree)
    assert "lifecycle" not in resources(tree, "aws_xray_group")[0]


def test_preview_explains_task_local_instrumentation_and_shared_permissions():
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    assert preview.connection_type == "traces_to"
    assert {item.resource_type for item in preview.resources} == {
        "aws_iam_role_policy",
        "aws_cloudwatch_log_group",
    }
    message = " ".join(item.message for item in preview.issues)
    for text in [
        "instrumentation",
        "sampling",
        "4317/4318",
        "64 CPU",
        "256 MiB",
        "wildcard",
        "AND",
        "five seconds",
        "native ECS",
        "once",
        "nonzero",
        "no legacy UDP",
    ]:
        assert text in message


@needs_terraform
def test_emitted_collector_configuration_uses_native_identity_and_local_listeners(
    tmp_path,
):
    config = configuration(tmp_path)
    assert config["receivers"] == {
        "otlp": {
            "protocols": {
                "grpc": {"endpoint": "127.0.0.1:4317"},
                "http": {"endpoint": "127.0.0.1:4318"},
            }
        }
    }
    assert config["processors"]["attributes/xray_identity"]["actions"] == [
        {
            "key": "iac_ecs_cluster_arn",
            "value": native_values()["aws_ecs_cluster.source-resource.arn"],
            "action": "upsert",
        }
    ]
    assert config["exporters"]["awsxray"] == {
        "region": "us-east-1",
        "local_mode": True,
        "indexed_attributes": ["iac_ecs_cluster_arn"],
        "index_all_attributes": False,
        "telemetry": {"enabled": False},
    }
    assert set(config["service"]["pipelines"]) == {"traces"}
    assert "sampling" not in config["processors"]


@needs_terraform
@pytest.mark.parametrize("prometheus", [False, True])
@pytest.mark.parametrize(
    "mode,failed",
    [
        ("valid", None),
        ("reserved", 0),
        ("empty", 0),
        ("cpu", 1),
        ("memory", 1),
        ("launch", 2),
        ("subnets", 2),
        ("groups", 2),
        ("tcp_port", 3),
        ("tcp_range", 3),
        ("secret", 4),
    ],
)
def test_task_guards_cover_capacity_placement_and_collector_ownership(
    tmp_path, prometheus, mode, failed
):
    values = native_values(prometheus=prometheus)
    containers = json.loads(values["var.container_definitions"])
    if mode == "reserved":
        containers[0]["name"] = COLLECTOR_NAME
    elif mode == "empty":
        containers = []
    elif mode == "cpu":
        values["var.ecs_cpu"] = "64"
    elif mode == "memory":
        values["var.ecs_memory"] = "256"
    elif mode == "launch":
        values["var.ecs_launch_type"] = "EC2"
    elif mode == "subnets":
        values["var.subnet_ids"] = []
    elif mode == "groups":
        values["var.security_group_ids"] = []
    elif mode == "tcp_port":
        containers[0]["portMappings"] = [{"containerPort": 4318}]
    elif mode == "tcp_range":
        containers[0]["portMappings"] = [{"containerPortRange": "4300-4400"}]
    elif mode == "secret":
        containers[0]["secrets"] = [
            {"name": "OTEL_TRACES_EXPORTER", "valueFrom": "external"}
        ]
    values["var.container_definitions"] = json.dumps(containers)
    guards = xray_task_preconditions(prometheus=prometheus)
    assert evaluate(
        tmp_path,
        "[" + ", ".join(str(item["condition"]) for item in guards) + "]",
        values,
    ) == [index != failed for index in range(len(guards))]


@needs_terraform
@pytest.mark.parametrize(
    "mapping,expected",
    [
        ({"containerPort": 4317, "protocol": "udp"}, True),
        ({"containerPortRange": "8000-8100"}, True),
        ({"containerPort": 4317, "protocol": "other"}, False),
    ],
)
def test_nonconflicting_port_mappings_are_supported(tmp_path, mapping, expected):
    values = native_values()
    values["var.container_definitions"] = json.dumps(
        [{"name": "application", "portMappings": [mapping]}]
    )
    assert (
        evaluate(
            tmp_path, xray_task_preconditions(prometheus=False)[3]["condition"], values
        )
        is expected
    )


@needs_terraform
def test_combined_collectors_require_capacity_for_both_and_distinct_scrape_ports(
    tmp_path,
):
    values = native_values(prometheus=True)
    values["var.ecs_memory"] = "512"
    values["var.prometheus_collection.application_metrics_port"] = 4317
    guards = xray_task_preconditions(prometheus=True)
    assert evaluate(
        tmp_path,
        "[" + ", ".join(str(item["condition"]) for item in guards) + "]",
        values,
    ) == [True, False, True, True, True, False]


@needs_terraform
@pytest.mark.parametrize(
    "mode,expected",
    [
        ("valid", [True] * 4),
        ("malformed", [False, False, True, True]),
        ("name", [False, True, True, True]),
        ("account", [True, False, True, True]),
        ("region", [True, False, True, True]),
        ("partition", [True, False, True, True]),
        ("empty", [False, True, True, True]),
    ],
)
def test_group_membership_guards_validate_native_identity_and_scope(
    tmp_path, mode, expected
):
    values = native_group_values()
    member = values["var.xray_ecs_clusters"]["diagram-node"]
    if mode == "malformed":
        member["arn"] = "invalid"
    elif mode == "name":
        member["name"] = "Other"
    elif mode == "empty":
        values["var.xray_ecs_clusters"] = {}
    elif mode in {"account", "region", "partition"}:
        key = {
            "account": "data.aws_caller_identity.xray_tracing.account_id",
            "region": "data.aws_region.xray_tracing.region",
            "partition": "data.aws_partition.xray_tracing.partition",
        }[mode]
        values[key] = {
            "account": "999999999999",
            "region": "eu-west-1",
            "partition": "aws-cn",
        }[mode]
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in ecs_group_preconditions())
        + "]"
    )
    assert evaluate(tmp_path, expression, values) == expected


@needs_terraform
@given(
    names=st.lists(resource_name_st, min_size=1, max_size=3, unique=True),
    combined=st.booleans(),
)
@settings(max_examples=6, deadline=None)
def test_group_filter_unions_ecs_annotations_and_lambda_members_with_existing_predicate(
    names, combined
):
    values = native_group_values()
    members = {
        f"node-{index}": {
            "arn": f"arn:aws:ecs:us-east-1:123456789012:cluster/{name}",
            "name": name,
        }
        for index, name in enumerate(names)
    }
    values["var.xray_ecs_clusters"] = members
    selectors = [ecs_group_selectors()]
    expected = [
        f'annotation.iac_ecs_cluster_arn = "{member["arn"]}"'
        for member in members.values()
    ]
    if combined:
        selectors.insert(0, lambda_group_selectors())
        expected.insert(
            0,
            '(service(id(name: "checkout", type: "AWS::Lambda", account.id: "123456789012")) OR service(id(name: "checkout", type: "AWS::Lambda::Function", account.id: "123456789012")))',
        )
    with TemporaryDirectory() as directory:
        actual = evaluate(Path(directory), group_filter_expression(selectors), values)
    assert actual == f"({' OR '.join(expected)}) AND (responsetime > 5 OR fault)"


@needs_terraform
@pytest.mark.parametrize("mixed", [False, True])
def test_serialized_containers_preserve_secrets_mounts_and_unrelated_environment(
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
    )[1]
    containers = [
        {
            "name": "source-resource",
            "image": "application",
            "cpu": 64,
            "memory": 256,
            "environment": [
                {"name": "KEEP", "value": "${literal}"},
                {"name": "OTEL_SERVICE_NAME", "value": "OriginalService"},
                {
                    "name": "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
                    "value": "https://old.example",
                },
            ],
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
    values = native_values(prometheus=mixed)
    values.update(
        {
            "var.container_definitions": json.dumps(containers),
            "local.xray_collector_configuration": "trace config",
            "aws_cloudwatch_log_group.source-resource_xray.name": "/aws/ecs/source-resource/xray",
        }
    )
    if mixed:
        values.update(
            {
                "local.runtime_secrets": [
                    {
                        "container": "source-resource",
                        "name": "SECRET",
                        "valueFrom": "managed-secret",
                    }
                ],
                "local.efs_mounts": [
                    {
                        "container": "source-resource",
                        "name": "managed-efs",
                        "path": "/mnt/efs",
                        "read_only": False,
                    }
                ],
                "local.prometheus_collector_configuration": "metrics config",
                "aws_cloudwatch_log_group.source-resource_prometheus.name": "/aws/ecs/source-resource/prometheus",
                "data.aws_region.ecs_prometheus.region": "us-east-1",
            }
        )
    result = json.loads(evaluate(tmp_path, expression, values))
    app, collector = result[:2]
    environment = {item["name"]: item["value"] for item in app["environment"]}
    assert environment == {
        "KEEP": "${literal}",
        "OTEL_SERVICE_NAME": "OriginalService",
        **TRACE_ENVIRONMENT,
    }
    assert len(app["environment"]) == len(environment)
    assert app["secrets"][0] == containers[0]["secrets"][0]
    assert app["mountPoints"][0] == containers[0]["mountPoints"][0]
    if mixed:
        assert app["secrets"][1]["valueFrom"] == "managed-secret"
        assert app["mountPoints"][1]["sourceVolume"] == "managed-efs"
        assert len(result) == 3 and result[2]["name"] == "iac-prometheus-collector"
        assert not any(
            item["name"] in TRACE_ENVIRONMENT for item in result[2]["environment"]
        )
    assert collector["name"] == COLLECTOR_NAME and collector["image"] == COLLECTOR_IMAGE
    assert (
        collector["essential"] is False
        and collector["cpu"] == 64
        and collector["memory"] == 256
    )
    assert (
        not collector.get("secrets")
        and not collector.get("mountPoints")
        and not collector.get("portMappings")
    )


@needs_terraform
def test_managed_secret_injection_cannot_override_tracing_configuration(tmp_path):
    payload = mixed_architecture()
    tree = generate(payload)
    content = next(
        content
        for content in tree.values()
        if 'resource "aws_ecs_task_definition"' in content
    )
    condition = next(
        condition
        for condition, message in re.findall(
            r'condition = ([\s\S]*?)\n\s+error_message = "([^\"]+)"', content
        )
        if message.startswith("Application secrets")
    )
    values = native_values(prometheus=True)
    values["local.runtime_secrets"] = [
        {
            "container": "source-resource",
            "name": "OTEL_TRACES_EXPORTER",
            "valueFrom": "managed-secret",
        }
    ]
    values["local.efs_mounts"] = []
    assert evaluate(tmp_path, condition, values) is False


@needs_terraform
def test_upload_policy_is_regional_and_does_not_grant_sampling_or_telemetry(tmp_path):
    content = file_with(generate(architecture()), "/source-resource/xray_collection.tf")
    expression = re.search(r"policy = jsonencode\(([\s\S]+)\)\n}", content)[1]
    actual = evaluate(
        tmp_path, expression, {"data.aws_region.ecs_xray.region": "eu-west-1"}
    )
    assert actual["Statement"] == [
        {
            "Action": ["xray:PutTraceSegments"],
            "Effect": "Allow",
            "Resource": "*",
            "Condition": {"StringEquals": {"aws:RequestedRegion": "eu-west-1"}},
        }
    ]


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode",
    [
        "plain",
        "shared_group",
        "multiple_groups",
        "combined_producers",
        "mixed",
        "regional",
        "managed_network",
    ],
)
def test_projects_validate_and_have_acyclic_graphs(tmp_path, mode):
    payload = mixed_architecture() if mode == "mixed" else architecture()
    if mode == "shared_group":
        source = deepcopy(payload["resources"][0])
        source.update(name="other-task", id="other-task")
        source["config"].update(cluster_name="OtherCluster", task_family="OtherTask")
        payload["resources"].append(source)
        payload["connections"].append(
            dict(payload["connections"][0], source="other-task", source_id="other-task")
        )
    elif mode == "multiple_groups":
        group = deepcopy(payload["resources"][1])
        group.update(name="other-group", id="other-group")
        group["config"]["group_name"] = "OtherGroup"
        payload["resources"].append(group)
        payload["connections"].append(
            dict(
                payload["connections"][0], target="other-group", target_id="other-group"
            )
        )
    elif mode == "combined_producers":
        bind_lambda(payload)
    elif mode == "regional":
        for item in payload["resources"]:
            item["provider_region"] = "eu-west-1"
    elif mode == "managed_network":
        for service, field in [
            (ServiceType.SUBNET, "subnet_ids"),
            (ServiceType.SECURITY_GROUP, "security_group_ids"),
        ]:
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
                    target="source-resource",
                    target_id="src",
                    source=service.value,
                    source_id=service.value,
                )
            )
    tree = generate(payload)
    if mode == "mixed":
        task = resources(tree, "aws_ecs_task_definition")[0]
        assert len(task["lifecycle"][0]["precondition"]) == 15
        assert len(resources(tree, "aws_cloudwatch_log_group")) == 2
        assert "module.traces.grafana_group_filter" in file_with(
            tree, "/environments/dev/main.tf"
        )
        assert "aws_xray_group.traces.filter_expression" in file_with(
            tree, "/traces/outputs.tf"
        )
    payload["connections"] = list(reversed(payload["connections"] * 2))
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
