import hashlib
import json
import re
from copy import deepcopy

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.ecr_eks import eks_image_preconditions, pull_role_preconditions
from app.generators.ecr_eks_manifests import image_locals
from app.models.connection_configs.ecr_eks import EcrEksConfig
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
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.ECR, ServiceType.EKS, None, {})
    )


def settings_for(**settings):
    return {
        "deployment_name": "web",
        "pull_role_arn": "arn:aws:iam::123456789012:role/workers/image-pull",
        **settings,
    }


def test_native_inputs_external_roles_and_manual_patches():
    payload = architecture()
    tree = generate(payload)
    text = "\n".join(tree.values())
    for output in ("repository_arn", "repository_url", "repository_name"):
        assert f"module.source-resource.{output}" in text
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert policy["for_each"] == "${local.registry_pull_roles}"
    assert policy["role"] == "${data.aws_iam_role.registry_images[each.key].name}"
    assert len(policy["lifecycle"][0]["precondition"]) == 9
    assert policy["name_prefix"] == "ecr-eks-images-"
    for name in ("ecr_image_bindings", "ecr_image_patches", "ecr_image_target"):
        assert f'output "{name}"' in text
    for forbidden in (
        "aws_iam_role",
        "aws_eks_node_group",
        "aws_eks_fargate_profile",
        "aws_eks_access_entry",
        "kubernetes_deployment",
        "kubernetes_secret",
        "aws_ecr_authorization_token",
    ):
        assert not resources(tree, forbidden)
    assert "local-exec" not in text and "GetAuthorizationToken" in text
    cluster = resources(tree, "aws_eks_cluster")[0]
    assert "access_config" not in cluster
    guide = file_with(tree, "/ECR-IMAGES.md")
    assert "--type strategic" in guide and "--dry-run=server" in guide
    assert "terraform output -json target_resource_outputs" in guide
    previews = ConnectionPreviewer().preview_all(project(payload))
    assert len(previews[0].resources) == 1
    assert any("absent container name" in issue.message for issue in previews[0].issues)
    payload["connections"] = []
    assert not resources(generate(payload), "aws_iam_role_policy")


@given(
    name=resource_name_st,
    version=st.sampled_from(["release-1.2", "sha256:" + "a" * 64]),
    count=st.integers(1, 4),
    copies=st.integers(1, 3),
)
@settings(max_examples=15, deadline=None)
def test_property_sharing_containers_compute_roles_and_duplicate_order(
    name, version, count, copies
):
    payload = architecture()
    payload["resources"][0]["config"]["repository_name"] = "team/" + name + "0"
    original = deepcopy(payload["connections"][0])
    payload["connections"] = []
    for index in range(count):
        payload["connections"].append(
            dict(
                original,
                connection_config=settings_for(
                    namespace="app-" + name + "0",
                    deployment_name="web." + name + "0",
                    container_name="app",
                    image_version=version,
                    pull_role_arn=f"arn:aws:iam::123456789012:role/workers/role-{index}",
                ),
            )
        )
        payload["connections"].append(
            dict(
                original,
                connection_config=settings_for(
                    container_name=f"helper-{index}", image_version="helper"
                ),
            )
        )
    payload["resources"].append(
        dict(payload["resources"][1], name="second-cluster", id="second")
    )
    payload["connections"].append(
        dict(
            original,
            target="second-cluster",
            target_id="second",
            connection_config=settings_for(image_version=version),
        )
    )
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * copies))
    assert generate(payload) == expected
    assert len(resources(expected, "aws_ecr_repository")) == 1
    assert len(resources(expected, "aws_eks_cluster")) == 2
    assert len(resources(expected, "aws_iam_role_policy")) == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("namespace", ""),
        ("namespace", "Kube"),
        ("namespace", "x" * 64),
        ("deployment_name", ""),
        ("deployment_name", "x..y"),
        ("deployment_name", "x.-y"),
        ("deployment_name", "x" * 254),
        ("deployment_name", "${workload}"),
        ("container_name", "App"),
        ("container_name", "x.y"),
        ("container_name", "x" * 64),
        ("pull_role_arn", "arn:aws:iam::123456789012:policy/images"),
        ("pull_role_arn", "${role}"),
        ("pull_role_type", "irsa"),
        ("pull_role_type", "cluster"),
        ("image_version", "sha256:" + "a" * 63),
        ("image_version", "${tag}"),
        ("image_version", True),
        ("deployment_name", True),
        ("pull_role_arn", 1),
    ],
)
def test_invalid_connection_fields(field, value):
    with pytest.raises(ValidationError):
        EcrEksConfig(**settings_for(**{field: value}))


@pytest.mark.parametrize(
    "case",
    [
        "version",
        "repository",
        "role-type",
        "cross-cluster-role-type",
        "cluster-role",
        "repository-name",
        "placement",
        "region",
        "environment-region",
    ],
)
def test_conflicts_and_prerequisites(case):
    payload = architecture()
    original = payload["connections"][0]
    if case == "version":
        payload["connections"].append(
            dict(original, connection_config=settings_for(image_version="other"))
        )
    elif case == "repository":
        payload["resources"].append(
            dict(payload["resources"][0], name="other", id="other")
        )
        payload["connections"].append(dict(original, source="other", source_id="other"))
    elif case in {"role-type", "cross-cluster-role-type"}:
        other = dict(original, connection_config=settings_for(pull_role_type="fargate"))
        if case == "cross-cluster-role-type":
            payload["resources"].append(
                dict(payload["resources"][1], name="other", id="other")
            )
            other.update(target="other", target_id="other")
        payload["connections"].append(other)
    elif case == "cluster-role":
        original["connection_config"]["pull_role_arn"] = payload["resources"][1][
            "config"
        ]["cluster_role_arn"]
    elif case == "repository-name":
        payload["resources"][0]["config"]["repository_name"] = "$(bad)"
    elif case == "placement":
        payload["resources"][1]["config"]["subnet_ids"] = []
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
    role = "arn:aws:iam::123456789012:role/workers/image-pull"
    key = hashlib.sha256(role.encode()).hexdigest()
    return {
        "var.registry_images": {
            "selected": {
                **EcrEksConfig(**settings_for()).model_dump(),
                "arn": "arn:aws:ecr:us-east-1:123456789012:repository/team/app",
                "url": "123456789012.dkr.ecr.us-east-1.amazonaws.com/team/app",
                "name": "team/app",
            }
        },
        "var.cluster_role_arn": "arn:aws:iam::123456789012:role/cluster/control-plane",
        "aws_eks_cluster.target-resource": {
            "arn": "arn:aws:eks:us-east-1:123456789012:cluster/application",
            "name": "application",
        },
        "data.aws_iam_role.registry_images[each.key].arn": role,
        "data.aws_iam_role.registry_images[each.key].assume_role_policy": json.dumps(
            {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "sts:AssumeRole",
                        "Principal": {"Service": "ec2.amazonaws.com"},
                    }
                ]
            }
        ),
        "data.aws_partition.registry_images.partition": "aws",
        "data.aws_partition.registry_images.dns_suffix": "amazonaws.com",
        "data.aws_region.registry_images.region": "us-east-1",
        "data.aws_caller_identity.registry_images.account_id": "123456789012",
        "each.key": key,
        "each.value": [role],
    }


def evaluate_locals(tmp_path, values):
    for name, expression in image_locals().items():
        values[f"local.{name}"] = evaluate(tmp_path, str(expression), values)


@needs_terraform
@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "fargate",
        "gov",
        "china",
        "account",
        "region",
        "partition",
        "url",
        "name",
        "tag",
        "namespace",
        "deployment",
        "container",
        "cluster-account",
        "role-account",
        "role-path",
        "cluster-role",
        "trust",
        "deny",
        "mixed-role-type",
        "conflict",
        "singleton-trust",
        "list-trust",
    ],
)
def test_native_guards(tmp_path, case):
    values = native_values()
    binding = values["var.registry_images"]["selected"]
    trust = json.loads(
        values["data.aws_iam_role.registry_images[each.key].assume_role_policy"]
    )
    if case == "fargate":
        binding["pull_role_type"] = "fargate"
        trust["Statement"][0]["Principal"]["Service"] = "eks-fargate-pods.amazonaws.com"
    elif case in {"gov", "china"}:
        partition, region, suffix = (
            ("aws-us-gov", "us-gov-west-1", "amazonaws.com")
            if case == "gov"
            else ("aws-cn", "cn-north-1", "amazonaws.com.cn")
        )
        for key in list(values):
            if key in {
                "var.cluster_role_arn",
                "data.aws_iam_role.registry_images[each.key].arn",
            }:
                values[key] = values[key].replace("arn:aws:", f"arn:{partition}:")
        binding["pull_role_arn"] = values[
            "data.aws_iam_role.registry_images[each.key].arn"
        ]
        values["each.key"] = hashlib.sha256(
            binding["pull_role_arn"].encode()
        ).hexdigest()
        values["each.value"] = [binding["pull_role_arn"]]
        binding["arn"] = (
            f"arn:{partition}:ecr:{region}:123456789012:repository/team/app"
        )
        binding["url"] = f"123456789012.dkr.ecr.{region}.{suffix}/team/app"
        values["aws_eks_cluster.target-resource"]["arn"] = (
            f"arn:{partition}:eks:{region}:123456789012:cluster/application"
        )
        values.update(
            {
                "data.aws_partition.registry_images.partition": partition,
                "data.aws_region.registry_images.region": region,
                "data.aws_partition.registry_images.dns_suffix": suffix,
            }
        )
    elif case in {"account", "region", "partition"}:
        old, new = {
            "account": ("123456789012", "111111111111"),
            "region": ("us-east-1", "eu-west-1"),
            "partition": ("arn:aws:", "arn:aws-cn:"),
        }[case]
        binding["arn"] = binding["arn"].replace(old, new)
    elif case in {"url", "name", "tag", "namespace", "deployment", "container"}:
        binding[
            {
                "tag": "image_version",
                "deployment": "deployment_name",
                "container": "container_name",
            }.get(case, case)
        ] = "${bad}"
    elif case == "cluster-account":
        values["aws_eks_cluster.target-resource"]["arn"] = values[
            "aws_eks_cluster.target-resource"
        ]["arn"].replace("123456789012", "111111111111")
    elif case == "role-account":
        binding["pull_role_arn"] = binding["pull_role_arn"].replace(
            "123456789012", "111111111111"
        )
    elif case == "role-path":
        values["data.aws_iam_role.registry_images[each.key].arn"] = binding[
            "pull_role_arn"
        ].replace("workers/", "other/")
    elif case == "cluster-role":
        values["var.cluster_role_arn"] = binding["pull_role_arn"]
    elif case == "trust":
        trust["Statement"][0]["Principal"] = {"Service": "eks.amazonaws.com"}
    elif case == "deny":
        trust["Statement"][0]["Effect"] = "Deny"
    elif case in {"mixed-role-type", "conflict"}:
        other = deepcopy(binding)
        other["pull_role_type" if case == "mixed-role-type" else "image_version"] = (
            "fargate" if case == "mixed-role-type" else "other"
        )
        values["var.registry_images"]["other"] = other
    elif case == "singleton-trust":
        trust["Statement"] = trust["Statement"][0]
    elif case == "list-trust":
        trust["Statement"][0].update(
            Action=["sts:AssumeRole"],
            Principal={"Service": ["ssm.amazonaws.com", "ec2.amazonaws.com"]},
        )
        trust["Statement"].append(
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Principal": {"Federated": "external"},
            }
        )
    values["data.aws_iam_role.registry_images[each.key].assume_role_policy"] = (
        json.dumps(trust)
    )
    evaluate_locals(tmp_path, values)
    conditions = (
        eks_image_preconditions("aws_eks_cluster.target-resource")
        + pull_role_preconditions()
    )
    assert evaluate(
        tmp_path,
        "alltrue([" + ", ".join(str(item["condition"]) for item in conditions) + "])",
        values,
    ) is (case in {"valid", "fargate", "gov", "china", "singleton-trust", "list-trust"})


@needs_terraform
@pytest.mark.parametrize("version", ["release", "sha256:" + "a" * 64])
def test_patches_aggregate_images_and_policies_scope_each_role(tmp_path, version):
    values = native_values()
    first = values["var.registry_images"]["selected"]
    first["image_version"] = version
    other = dict(
        first,
        container_name="helper",
        name="team/helper",
        arn=first["arn"].replace("team/app", "team/helper"),
        url=first["url"].replace("team/app", "team/helper"),
    )
    second_role = dict(
        first, pull_role_arn="arn:aws:iam::123456789012:role/workers/second"
    )
    values["var.registry_images"].update(
        helper=other,
        second=second_role,
        duplicate=deepcopy(first),
        other_namespace=dict(first, namespace="another"),
    )
    evaluate_locals(tmp_path, values)
    patches = values["local.registry_image_patches"]
    patch = patches["default/web"]
    assert patch["metadata"] == {"name": "web", "namespace": "default"}
    assert set(patches) == {"default/web", "another/web"}
    assert patch["apiVersion"] == "apps/v1" and patch["kind"] == "Deployment"
    selected = patch["spec"]["template"]["spec"]["containers"]
    assert [item["name"] for item in selected] == ["app", "helper"]
    assert all(set(item) == {"name", "image"} for item in selected)
    assert (
        selected[0]["image"]
        == first["url"] + ("@" if version.startswith("sha256:") else ":") + version
    )
    assert (
        yaml.safe_load(
            evaluate(
                tmp_path,
                'yamlencode(local.registry_image_patches["default/web"])',
                values,
            )
        )
        == patch
    )
    content = file_with(generate(architecture()), "/registry_images.tf")
    expression = re.search(r"  policy = (.*)", content)[1]
    for role, expected in [
        (first["pull_role_arn"], [first["arn"], other["arn"]]),
        (second_role["pull_role_arn"], [first["arn"]]),
    ]:
        values["each.value"] = [role]
        policy = json.loads(evaluate(tmp_path, expression, values))
        assert policy["Statement"][0] == {
            "Effect": "Allow",
            "Action": ["ecr:GetAuthorizationToken"],
            "Resource": "*",
        }
        assert policy["Statement"][1]["Resource"] == sorted(expected)
        assert policy["Statement"][1]["Action"] == [
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage",
        ]


def add_existing(payload, source, target, **config):
    template = connection_architecture(resolve_spec(source, target, None, {}))
    selected = template["resources"][0 if source != ServiceType.EKS else 1]
    name = "connected-" + selected["service_type"]
    selected.update(name=name, id=name)
    payload["resources"].append(selected)
    edge = template["connections"][0]
    if source == ServiceType.EKS:
        edge.update(
            target=name, target_id=name, source="target-resource", source_id="tgt"
        )
    else:
        edge.update(source=name, source_id=name)
    edge["connection_config"].update(config)
    payload["connections"].append(edge)


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode",
    [
        "node",
        "fargate",
        "digest",
        "duplicates",
        "multi-role",
        "multi-repository",
        "shared-clusters",
        "regional",
        "placement",
        "observability",
        "efs",
        "fis",
    ],
)
def test_provider_validation_and_acyclic_composition(tmp_path, mode):
    payload = architecture()
    if mode in {"fargate", "digest"}:
        payload["connections"][0]["connection_config"].update(
            {"pull_role_type": "fargate"}
            if mode == "fargate"
            else {"image_version": "sha256:" + "a" * 64}
        )
    elif mode == "duplicates":
        payload["connections"] *= 3
    elif mode == "multi-role":
        payload["connections"].append(
            dict(
                payload["connections"][0],
                connection_config=settings_for(
                    pull_role_arn="arn:aws:iam::123456789012:role/workers/second"
                ),
            )
        )
    elif mode == "multi-repository":
        payload["resources"].append(
            dict(payload["resources"][0], name="helper-images", id="helper")
        )
        payload["connections"].append(
            dict(
                payload["connections"][0],
                source="helper-images",
                source_id="helper",
                connection_config=settings_for(container_name="helper"),
            )
        )
    elif mode == "shared-clusters":
        payload["resources"].append(
            dict(payload["resources"][1], name="second-cluster", id="second")
        )
        payload["connections"].append(
            dict(payload["connections"][0], target="second-cluster", target_id="second")
        )
    elif mode == "regional":
        payload["resources"][0]["provider_region"] = "eu-west-1"
        payload["environments"][0]["variables"]["region"] = "us-west-2"
    elif mode == "placement":
        payload["resources"][1]["config"]["subnet_ids"] = []
        add_existing(payload, ServiceType.SUBNET, ServiceType.EKS)
    elif mode == "observability":
        add_existing(payload, ServiceType.EKS, ServiceType.CLOUDWATCH)
        add_existing(payload, ServiceType.EKS, ServiceType.MANAGED_PROMETHEUS)
    elif mode == "efs":
        add_existing(payload, ServiceType.EFS, ServiceType.EKS)
    elif mode == "fis":
        add_existing(payload, ServiceType.FAULT_INJECTION_SIMULATOR, ServiceType.EKS)
    tree = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    _write_tree(tmp_path, tree)
    environment = tmp_path / "connection-check/environments/dev"
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], environment
    )
    _run_terraform(["validate", "-no-color"], environment)
    _run_terraform(["graph", "-type=plan"], environment)
