import json
import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.ecr_ecs import registry_image_preconditions
from app.models.connection_configs.ecr_ecs import EcrEcsConfig
from app.models.input_models import ServiceType
from app.models.input_models.ecs_config import EcsConfig
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_ecs_logs_connections import mixed_architecture as logged_architecture
from tests.test_ecs_logs_connections import task_expression
from tests.test_eks_prometheus_connections import evaluate
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.ECR, ServiceType.ECS, None, {})
    )


def containers(name="target-resource"):
    return [
        {
            "name": name,
            "image": "old-image",
            "essential": True,
            "command": ["serve", "${literal}"],
            "environment": [{"name": "MODE", "value": "release"}],
            "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
        },
        {
            "name": "helper",
            "image": "public.ecr.aws/docker/library/busybox:latest",
            "essential": False,
        },
    ]


def add_image(payload, target="target-resource", target_id="tgt"):
    template = architecture()
    payload["resources"].append(
        dict(template["resources"][0], name="images", id="images")
    )
    payload["connections"].append(
        dict(
            template["connections"][0],
            source="images",
            source_id="images",
            target=target,
            target_id=target_id,
        )
    )


def test_native_images_execution_role_and_scoped_baseline():
    payload = architecture()
    ir = project(payload)
    preview = ConnectionPreviewer().preview_all(ir)[0]
    assert any("Push a compatible image" in issue.message for issue in preview.issues)
    assert any(
        item.resource_type == "aws_iam_role_policy" for item in preview.resources
    )
    tree = generate(payload)
    text = "\n".join(tree.values())
    for output in ("repository_arn", "repository_url", "repository_name"):
        assert f"module.source-resource.{output}" in text
    task = resources(tree, "aws_ecs_task_definition")[0]
    assert task["execution_role_arn"] == "${aws_iam_role.target-resource_role.arn}"
    assert "task_role_arn" not in task
    assert set(task["depends_on"]) == {
        "${aws_iam_role_policy.target-resource_policy}",
        "${aws_iam_role_policy.registry_images}",
    }
    assert len(task["lifecycle"][0]["precondition"]) == 6
    baseline = json.loads(file_with(tree, "/target-resource-policy.json"))
    actions = [
        action for statement in baseline["Statement"] for action in statement["Action"]
    ]
    assert "ecr:GetAuthorizationToken" in actions
    assert "ecr:BatchGetImage" not in actions
    assert "aws_ecr_authorization_token" not in text
    payload["connections"] = []
    unconnected = generate(payload)
    assert (
        "execution_role_arn" not in resources(unconnected, "aws_ecs_task_definition")[0]
    )
    assert "ecr:BatchGetImage" in file_with(unconnected, "/target-resource-policy.json")


@given(
    name=resource_name_st,
    version=st.sampled_from(["latest", "release-1.2", "sha256:" + "a" * 64]),
    copies=st.integers(1, 4),
)
@settings(max_examples=15, deadline=None)
def test_property_versions_shared_repository_and_connection_order(
    name, version, copies
):
    payload = architecture()
    payload["resources"][0]["config"]["repository_name"] = "team/" + name + "0"
    payload["resources"][1]["config"]["container_definitions"] = json.dumps(
        containers()
    )
    payload["connections"][0]["connection_config"] = {"image_version": version}
    payload["connections"].append(
        dict(
            payload["connections"][0],
            connection_config={"container_name": "helper", "image_version": "helper"},
        )
    )
    payload["resources"].append(
        dict(payload["resources"][1], name="second-task", id="second")
    )
    payload["connections"].append(
        dict(
            payload["connections"][0],
            target="second-task",
            target_id="second",
            connection_config={
                "container_name": "target-resource",
                "image_version": version,
            },
        )
    )
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * copies))
    assert generate(payload) == expected
    assert len(resources(expected, "aws_ecr_repository")) == 1
    assert len(resources(expected, "aws_ecs_task_definition")) == 2


@pytest.mark.parametrize(
    "value",
    [
        "",
        "${tag}",
        "x:y",
        "a" * 129,
        "sha256:" + "a" * 63,
        "sha256:" + "A" * 64,
        "repo:latest",
        True,
        1,
        None,
    ],
)
def test_invalid_image_versions(value):
    with pytest.raises(ValidationError):
        EcrEcsConfig(image_version=value)


@pytest.mark.parametrize("value", ["${container}", "a.b", "a" * 256, True, 1, None])
def test_invalid_container_selection(value):
    with pytest.raises(ValidationError):
        EcrEcsConfig(container_name=value)


@pytest.mark.parametrize(
    "value",
    [
        "[]",
        "{}",
        "not-json",
        '[{"name":"app"}]',
        '[{"name":"app","image":1}]',
        '[{"name":"app","image":""}]',
        '[{"name":"app","image":"x"},{"name":"app","image":"y"}]',
        '[{"name":"app","image":"x","memory":NaN}]',
    ],
)
def test_invalid_container_definitions(value):
    with pytest.raises(ValidationError):
        EcsConfig(container_definitions=value)


def test_container_configuration_normalizes_and_preserves_extra_fields():
    original = containers()
    assert (
        json.loads(
            EcsConfig(container_definitions=json.dumps(original)).container_definitions
        )
        == original
    )


@pytest.mark.parametrize(
    "case",
    [
        "version-conflict",
        "repository-conflict",
        "missing-container",
        "collector",
        "credentials",
        "unbound-private",
        "bad-repository",
        "launch",
        "subnets",
        "security-groups",
        "region",
        "environment-region",
    ],
)
def test_conflicts_and_prerequisites(case):
    payload = architecture()
    if case == "version-conflict":
        payload["connections"].append(
            dict(
                payload["connections"][0], connection_config={"image_version": "other"}
            )
        )
    elif case == "repository-conflict":
        payload["resources"].append(
            dict(payload["resources"][0], name="other", id="other")
        )
        payload["connections"].append(
            dict(payload["connections"][0], source="other", source_id="other")
        )
    elif case in {"missing-container", "collector"}:
        payload["connections"][0]["connection_config"] = {
            "container_name": "missing"
            if case == "missing-container"
            else "iac-prometheus-collector"
        }
    elif case in {"credentials", "unbound-private"}:
        original = containers()
        if case == "credentials":
            original[0]["repositoryCredentials"] = {"credentialsParameter": "external"}
        else:
            original[1]["image"] = (
                "123456789012.dkr.ecr.us-east-1.amazonaws.com/private:latest"
            )
        payload["resources"][1]["config"]["container_definitions"] = json.dumps(
            original
        )
    elif case == "bad-repository":
        payload["resources"][0]["config"]["repository_name"] = "$(danger)"
    elif case in {"launch", "subnets", "security-groups"}:
        key = {
            "launch": "ecs_launch_type",
            "subnets": "subnet_ids",
            "security-groups": "security_group_ids",
        }[case]
        payload["resources"][1]["config"][key] = "EC2" if case == "launch" else []
    else:
        payload["resources"][0]["provider_region"] = "eu-west-1"
        if case == "environment-region":
            payload["environments"].append(
                {"name": "prod", "variables": {"region": "us-east-1"}}
            )
    with pytest.raises(
        CrossRegionConnectionError
        if case in {"region", "environment-region"}
        else InvalidConnectionConfigError
    ):
        generate(payload)


def native_values():
    return {
        "var.registry_images": {
            "target-resource": {
                "arn": "arn:aws:ecr:us-east-1:123456789012:repository/team/app",
                "url": "123456789012.dkr.ecr.us-east-1.amazonaws.com/team/app",
                "name": "team/app",
                "image_version": "release",
            }
        },
        "var.container_definitions": json.dumps(containers()),
        "var.ecs_launch_type": "FARGATE",
        "var.subnet_ids": ["subnet-12345678"],
        "var.security_group_ids": ["sg-12345678"],
        "data.aws_partition.registry_images.partition": "aws",
        "data.aws_partition.registry_images.dns_suffix": "amazonaws.com",
        "data.aws_region.registry_images.region": "us-east-1",
        "data.aws_caller_identity.registry_images.account_id": "123456789012",
    }


@needs_terraform
@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "digest",
        "gov",
        "china",
        "account",
        "region",
        "partition",
        "name",
        "url",
        "tag",
        "credentials",
        "unbound-private",
        "missing-container",
        "duplicates",
        "placement",
        "launch",
    ],
)
def test_native_override_guards(tmp_path, case):
    values = native_values()
    binding = values["var.registry_images"]["target-resource"]
    original = containers()
    if case in {"gov", "china"}:
        partition, region, suffix = (
            ("aws-us-gov", "us-gov-west-1", "amazonaws.com")
            if case == "gov"
            else ("aws-cn", "cn-north-1", "amazonaws.com.cn")
        )
        values["data.aws_partition.registry_images.partition"] = partition
        values["data.aws_region.registry_images.region"] = region
        values["data.aws_partition.registry_images.dns_suffix"] = suffix
        binding["arn"] = (
            f"arn:{partition}:ecr:{region}:123456789012:repository/team/app"
        )
        binding["url"] = f"123456789012.dkr.ecr.{region}.{suffix}/team/app"
    elif case in {"account", "region", "partition"}:
        old, new = {
            "account": ("123456789012", "111111111111"),
            "region": ("us-east-1", "eu-west-1"),
            "partition": ("arn:aws:", "arn:aws-cn:"),
        }[case]
        binding["arn"] = binding["arn"].replace(old, new)
    elif case in {"name", "url", "tag", "digest"}:
        binding[
            {
                "name": "name",
                "url": "url",
                "tag": "image_version",
                "digest": "image_version",
            }[case]
        ] = "sha256:" + "a" * 64 if case == "digest" else "${bad}"
    elif case == "credentials":
        original[0]["repositoryCredentials"] = {"credentialsParameter": "external"}
    elif case == "unbound-private":
        original[1]["image"] = (
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/private:latest"
        )
    elif case == "missing-container":
        values["var.registry_images"]["missing"] = values["var.registry_images"].pop(
            "target-resource"
        )
    elif case == "duplicates":
        original.append(original[0])
    elif case == "placement":
        values["var.security_group_ids"] = []
    elif case == "launch":
        values["var.ecs_launch_type"] = "EC2"
    values["var.container_definitions"] = json.dumps(original)
    expression = (
        "alltrue(["
        + ", ".join(str(item["condition"]) for item in registry_image_preconditions())
        + "])"
    )
    assert evaluate(tmp_path, expression, values) is (
        case in {"valid", "digest", "gov", "china"}
    )


@needs_terraform
@pytest.mark.parametrize("version", ["release-1.2", "sha256:" + "a" * 64])
def test_effective_images_preserve_containers_and_pull_policy(tmp_path, version):
    payload = architecture()
    payload["resources"][1]["config"]["container_definitions"] = json.dumps(
        containers()
    )
    tree = generate(payload)
    content = file_with(tree, "/registry_images.tf")
    values = native_values()
    values["var.registry_images"]["target-resource"]["image_version"] = version
    expression = re.search(r"  registry_images = (.*)", content)[1]
    images = evaluate(tmp_path, expression, values)
    values["local.registry_images"] = images
    actual = json.loads(evaluate(tmp_path, task_expression(tree), values))
    variable = re.search(
        r'variable "container_definitions" \{(.*?)\n\}',
        file_with(tree, "/ecs/target-resource/variables.tf"),
        re.S,
    )[1]
    default = re.search(r"  default\s+= (.*)", variable)[1]
    assert json.loads(evaluate(tmp_path, default, {})) == containers()
    expected = containers()
    expected[0]["image"] = (
        values["var.registry_images"]["target-resource"]["url"]
        + ("@" if version.startswith("sha256:") else ":")
        + version
    )
    assert actual == expected
    policy_expression = re.search(r"  policy = (.*)", content)[1]
    policy = json.loads(evaluate(tmp_path, policy_expression, values))
    assert policy["Statement"] == [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
            ],
            "Resource": [values["var.registry_images"]["target-resource"]["arn"]],
        }
    ]


@needs_terraform
def test_image_replacement_composes_with_application_features_and_collectors(tmp_path):
    from tests.test_ecs_logs_connections import configuration_expression
    from tests.test_ecs_logs_connections import native_values as log_values

    payload = logged_architecture()
    add_image(payload, "source-resource", "src")
    values = log_values()
    values.update(
        {
            "local.registry_images": {
                "source-resource": "123456789012.dkr.ecr.us-east-1.amazonaws.com/application:release"
            },
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
                    "name": "efs-volume",
                    "path": "/mnt/efs",
                    "read_only": False,
                }
            ],
            "local.xray_collector_configuration": "traces",
            "local.prometheus_collector_configuration": "metrics",
            "aws_cloudwatch_log_group.source-resource_xray.name": "/collector/traces",
            "aws_cloudwatch_log_group.source-resource_prometheus.name": "/collector/metrics",
            "data.aws_region.ecs_xray.region": "us-east-1",
            "data.aws_region.ecs_prometheus.region": "us-east-1",
        }
    )
    values["local.application_log_configurations"] = evaluate(
        tmp_path, configuration_expression(), values
    )
    result = json.loads(evaluate(tmp_path, task_expression(generate(payload)), values))
    assert len(result) == 3
    assert result[0]["image"] == values["local.registry_images"]["source-resource"]
    assert result[0]["secrets"][0]["valueFrom"] == "managed-secret"
    assert result[0]["mountPoints"][0]["sourceVolume"] == "efs-volume"
    assert result[0]["logConfiguration"]["options"]["awslogs-group"] == "/native/app"
    for collector in result[1:]:
        assert collector["image"].startswith("public.ecr.aws/aws-observability/")
        assert not collector.get("secrets") and not collector.get("mountPoints")


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode",
    [
        "default",
        "digest",
        "multi-repositories",
        "duplicates",
        "regional",
        "logs-collectors",
        "efs-secrets",
        "eventbridge",
        "placement",
        "load-balancer",
    ],
)
def test_provider_validation_and_acyclic_composition(tmp_path, mode):
    payload = architecture()
    if mode == "digest":
        payload["connections"][0]["connection_config"] = {
            "image_version": "sha256:" + "a" * 64
        }
    elif mode == "multi-repositories":
        payload["resources"][1]["config"]["container_definitions"] = json.dumps(
            containers()
        )
        add_image(payload)
        payload["connections"][-1]["connection_config"] = {
            "container_name": "helper",
            "image_version": "v2",
        }
    elif mode == "duplicates":
        payload["connections"] *= 3
    elif mode == "regional":
        payload["resources"][0]["provider_region"] = "eu-west-1"
        payload["environments"][0]["variables"]["region"] = "us-west-2"
    elif mode == "logs-collectors":
        payload = logged_architecture(encrypted=True)
        add_image(payload, "source-resource", "src")
    elif mode in {"efs-secrets", "eventbridge"}:
        if mode == "efs-secrets":
            from tests.test_efs_ecs_connections import mixed_architecture
        else:
            from tests.test_eventbridge_ecs_connections import (
                architecture as mixed_architecture,
            )
        payload = mixed_architecture()
        add_image(payload)
    elif mode == "placement":
        payload["resources"][1]["config"].update(subnet_ids=[], security_group_ids=[])
        for service, edge in [
            (ServiceType.SUBNET, "places"),
            (ServiceType.SECURITY_GROUP, "associates"),
        ]:
            template = connection_architecture(
                resolve_spec(service, ServiceType.ECS, edge, {})
            )
            name = service.value + "-placement"
            payload["resources"].append(
                dict(template["resources"][0], name=name, id=name)
            )
            payload["connections"].append(
                dict(template["connections"][0], source=name, source_id=name)
            )
    elif mode == "load-balancer":
        template = connection_architecture(
            resolve_spec(ServiceType.TARGET_GROUP, ServiceType.ECS, None, {})
        )
        payload["resources"].append(
            dict(template["resources"][0], name="application-targets", id="targets")
        )
        payload["connections"].append(
            dict(
                template["connections"][0],
                source="application-targets",
                source_id="targets",
            )
        )
    tree = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    if mode in {"logs-collectors", "efs-secrets"}:
        task = resources(tree, "aws_ecs_task_definition")[0]
        assert "${aws_iam_role_policy.registry_images}" in task["depends_on"]
        assert len(task["lifecycle"][0]["precondition"]) > 6
        assert "local.registry_images" in task_expression(tree)
        assert "local.runtime_secrets" in task_expression(tree)
    _write_tree(tmp_path, tree)
    environment = tmp_path / "connection-check/environments/dev"
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], environment
    )
    _run_terraform(["validate", "-no-color"], environment)
    _run_terraform(["graph", "-type=plan"], environment)
