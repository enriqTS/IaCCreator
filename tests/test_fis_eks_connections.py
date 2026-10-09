"""Pod fault targets preserve cluster ownership, role deduplication, and manual RBAC."""

import hashlib
import json
import re
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.eks_fis_access import access_preconditions
from app.generators.fis_eks import eks_fault_preconditions
from app.models.connection_configs.fis import SELECTION_MODES
from app.models.connection_configs.fis_eks import FisEksConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_eks_prometheus_connections import (
    architecture as prometheus_architecture,
)
from tests.test_eks_prometheus_connections import (
    connect_storage_and_grafana,
    evaluate,
)
from tests.test_fis_ec2_connections import architecture as ec2_architecture
from tests.test_fis_ecs_connections import architecture as ecs_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.FAULT_INJECTION_SIMULATOR, ServiceType.EKS, None, {})
    )


def native_values():
    role = "arn:aws:iam::123456789012:role/fis/experiment"
    return {
        "var.role_arn": role,
        "var.action_name": "fault_action",
        "var.fis_eks_cluster": {
            "arn": "arn:aws:eks:us-east-1:123456789012:cluster/application",
            "name": "application",
            "version": "1.30",
            "authentication_mode": "API_AND_CONFIG_MAP",
            "authorized_roles": [role],
        },
        "var.fis_eks_pods": {
            "namespace": "application",
            "deployment_name": "web",
            "selection_mode": "COUNT(1)",
            "service_account": "iacc-fis-012345abcdef",
            "kubernetes_group": "iacc-fis-"
            + hashlib.sha256(role.encode()).hexdigest()[:12],
        },
        "data.aws_partition.experiment.partition": "aws",
        "data.aws_region.experiment.region": "us-east-1",
        "data.aws_caller_identity.experiment.account_id": "123456789012",
    }


def add_experiment(payload, shared_role=True):
    source = deepcopy(payload["resources"][0])
    source.update(name="another-experiment", id="another-experiment")
    if not shared_role:
        source["config"]["role_arn"] = "arn:aws:iam::123456789012:role/fis/other"
    payload["resources"].append(source)
    edge = deepcopy(payload["connections"][0])
    edge.update(source=source["name"], source_id=source["id"])
    edge["connection_config"]["namespace"] = "other-application"
    payload["connections"].append(edge)


def test_native_target_access_ownership_and_input_only_role_output():
    tree = generate(architecture())
    template = resources(tree, "aws_fis_experiment_template")[0]
    action = template["action"][0]
    assert action["action_id"] == "aws:eks:pod-delete"
    assert action["parameter"][0]["key"] == "kubernetesServiceAccount"
    assert action["parameter"][0]["value"] == "${var.fis_eks_pods.service_account}"
    assert len(action["parameter"]) == 1
    assert action["target"][0]["key"] == "Pods"
    target = template["target"][0]
    assert target["resource_type"] == "aws:eks:pod"
    assert target["parameters"] == {
        "clusterIdentifier": "${var.fis_eks_cluster.arn}",
        "namespace": "${var.fis_eks_pods.namespace}",
        "selectorType": "deploymentName",
        "selectorValue": "${var.fis_eks_pods.deployment_name}",
    }
    assert (
        "filter" not in target
        and "resource_arns" not in target
        and "resource_tag" not in target
    )
    assert template["depends_on"] == ["${aws_iam_role_policy.fis_eks}"]
    assert template["stop_condition"][0]["source"] == "none"
    access = resources(tree, "aws_eks_access_entry")[0]
    assert access["for_each"] == "${var.fis_experiment_roles}"
    assert access["type"] == "STANDARD"
    assert access["cluster_name"] == "${aws_eks_cluster.target-resource.name}"
    assert "user_name" not in access
    assert not resources(tree, "aws_eks_access_policy_association")
    assert not resources(tree, "aws_iam_role")
    output = file_with(tree, "/source-resource/outputs.tf")
    assert "native_arn = data.aws_iam_role.fis_eks.arn" in output
    cluster_output = file_with(tree, "/target-resource/outputs.tf")
    assert "entry.principal_arn" in cluster_output
    assert "aws_eks_cluster.target-resource.version" in cluster_output
    assert "API_AND_CONFIG_MAP" in file_with(tree, "/target-resource/variables.tf")
    contribution = ConnectionProcessor().process_all(project(architecture()))
    assert {(r.module, r.filename) for r in contribution.resources} == {
        ("source-resource", "eks_targets.tf"),
        ("source-resource", "eks_pod_manifests.tf"),
        ("source-resource", "FIS-EKS-PODS.md"),
        ("target-resource", "fis_access.tf"),
    }
    assert not contribution.iam


@given(
    name=resource_name_st,
    selection=st.sampled_from(SELECTION_MODES),
    duplicates=st.integers(1, 4),
)
@settings(max_examples=20, deadline=None)
def test_names_selections_and_duplicates_are_deterministic(name, selection, duplicates):
    payload = architecture()
    payload["resources"][1]["name"] = "target-" + name
    payload["connections"][0]["target"] = "target-" + name
    payload["connections"][0]["connection_config"]["selection_mode"] = selection
    tree = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * duplicates))
    assert generate(payload) == tree


@pytest.mark.parametrize("shared", [True, False])
def test_shared_principals_aggregate_once_and_are_order_independent(shared):
    payload = architecture()
    add_experiment(payload, shared)
    contribution = ConnectionProcessor().process_all(project(payload))
    roles = next(i for i in contribution.inputs if i.name == "fis_experiment_roles")
    assert roles.value.count("fis_experiment_role") == (1 if shared else 2)
    assert "module.another-experiment.fis_experiment_role" in roles.value
    assert len(resources(generate(payload), "aws_eks_access_entry")) == 1
    assert len(resources(generate(payload), "aws_fis_experiment_template")) == 2
    baseline = generate(payload)
    payload["connections"].reverse()
    assert generate(payload) == baseline


@pytest.mark.parametrize(
    "field,value",
    [
        ("namespace", "kube-system"),
        ("namespace", "kube-public"),
        ("namespace", "kube-node-lease"),
        ("namespace", ""),
        ("namespace", "Bad"),
        ("namespace", "a/b"),
        ("namespace", "x" * 64),
        ("deployment_name", ""),
        ("deployment_name", "*"),
        ("deployment_name", "web."),
        ("deployment_name", "-web"),
        ("selection_mode", "COUNT(0)"),
        ("selection_mode", "COUNT(6)"),
        ("selection_mode", "PERCENT(50)"),
        ("selection_mode", None),
        ("action_id", "aws:eks:pod-cpu-stress"),
        ("gracePeriodSeconds", 0),
        ("selectorType", "labels"),
    ],
)
def test_invalid_config_and_selector_overrides_are_rejected(field, value):
    config = {"namespace": "application", "deployment_name": "web", field: value}
    with pytest.raises(ValidationError):
        FisEksConfig.model_validate(config)
    payload = architecture()
    payload["connections"][0]["connection_config"] = config
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize("field", ["namespace", "deployment_name"])
def test_workload_identity_is_required(field):
    payload = architecture()
    del payload["connections"][0]["connection_config"][field]
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("authentication_mode", "CONFIG_MAP"),
        ("eks_version", "1.29"),
        ("eks_version", "1.9"),
        ("eks_version", "latest"),
        ("eks_version", "1.30.1"),
    ],
)
def test_cluster_prerequisites_are_validated(field, value):
    payload = architecture()
    payload["resources"][1]["config"][field] = value
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize(
    "field,value",
    [("role_arn", "arn:aws:iam::123456789012:user/fis"), ("action_name", "bad/name")],
)
def test_invalid_experiment_identity_is_rejected(field, value):
    payload = architecture()
    payload["resources"][0]["config"][field] = value
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize(
    "field", ["namespace", "deployment_name", "selection_mode", "cluster"]
)
def test_conflicting_duplicate_targets_are_rejected(field):
    payload = architecture()
    edge = deepcopy(payload["connections"][0])
    if field == "cluster":
        cluster = dict(
            deepcopy(payload["resources"][1]), name="other-cluster", id="other-cluster"
        )
        payload["resources"].append(cluster)
        edge.update(target=cluster["name"], target_id=cluster["id"])
    else:
        edge["connection_config"][field] = (
            "ALL" if field == "selection_mode" else "other"
        )
    payload["connections"].append(edge)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


@pytest.mark.parametrize("factory", [ec2_architecture, ecs_architecture])
@pytest.mark.parametrize("reverse", [True, False])
def test_mixed_target_families_are_rejected(factory, reverse):
    payload = architecture()
    other = factory()
    payload["resources"].append(dict(other["resources"][1], name="other", id="other"))
    payload["connections"].append(
        dict(other["connections"][0], target="other", target_id="other")
    )
    if reverse:
        payload["connections"].reverse()
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_cross_region_targets_are_rejected():
    payload = architecture()
    payload["resources"][1]["provider_region"] = "eu-west-1"
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)
    payload["environments"][0]["variables"]["region"] = "eu-central-1"
    assert generate(payload)


def test_service_account_identity_survives_source_rename():
    payload = architecture()
    original = ConnectionProcessor().process_all(project(payload))
    payload["resources"][0]["name"] = "renamed-experiment"
    payload["connections"][0]["source"] = "renamed-experiment"
    renamed = ConnectionProcessor().process_all(project(payload))
    assert next(i.value for i in original.inputs if i.name == "fis_eks_pods") == next(
        i.value for i in renamed.inputs if i.name == "fis_eks_pods"
    )


@needs_terraform
@pytest.mark.parametrize("path", ["fis/", "other/", ""])
def test_native_role_lookup_guard_requires_exact_path(tmp_path, path):
    policy = resources(generate(architecture()), "aws_iam_role_policy")[0]
    condition = policy["lifecycle"][0]["precondition"][-1]["condition"][2:-1]
    values = native_values()
    values["data.aws_iam_role.fis_eks.arn"] = (
        f"arn:aws:iam::123456789012:role/{path}experiment"
    )
    assert evaluate(tmp_path, condition, values) is (path == "fis/")


def test_explicit_api_authentication_and_endpoint_settings_are_preserved():
    payload = architecture()
    payload["resources"][1]["config"].update(
        authentication_mode="API",
        endpoint_private_access=True,
        eks_endpoint_public_access=False,
    )
    variables = file_with(generate(payload), "/target-resource/variables.tf")
    assert 'default     = "API"' in variables
    cluster = resources(generate(payload), "aws_eks_cluster")[0]
    assert (
        cluster["vpc_config"][0]["endpoint_public_access"]
        == "${var.eks_endpoint_public_access}"
    )
    before = deepcopy(payload)
    before["connections"] = []
    assert resources(generate(payload), "aws_eks_cluster") == resources(
        generate(before), "aws_eks_cluster"
    )


def test_preview_and_guide_explain_manual_access_and_namespace_scope():
    issues = ConnectionPreviewer().preview_all(project(architecture()))
    message = issues[0].issues[0].message
    for text in [
        "namespace",
        "manually",
        "cannot be reversed",
        "1.30",
        "PodDisruptionBudgets",
        "union",
        "Terraform destroy",
    ]:
        assert text in message
    guide = file_with(generate(architecture()), "/FIS-EKS-PODS.md")
    assert "source_resource_outputs" in guide
    assert "kubectl apply -f fis-pod-access.yaml" in guide
    assert "before removing" in guide


@needs_terraform
def test_emitted_policy_is_scoped_and_manifests_round_trip(tmp_path):
    tree = generate(architecture())
    policy_expression = re.search(
        r"  policy = (.*?)\n  lifecycle \{", file_with(tree, "/eks_targets.tf"), re.S
    )[1]
    values = native_values()
    policy = json.loads(evaluate(tmp_path, policy_expression, values))
    assert policy["Statement"][0]["Resource"] == values["var.fis_eks_cluster"]["arn"]
    assert policy["Statement"][0]["Action"] == ["eks:DescribeCluster"]
    assert policy["Statement"][1] == {
        "Effect": "Allow",
        "Action": ["ec2:DescribeSubnets", "tag:GetResources"],
        "Resource": "*",
        "Condition": {"StringEquals": {"aws:RequestedRegion": "us-east-1"}},
    }
    manifests_expression = re.search(
        r"fis_eks_manifests = (.*)\n\}", file_with(tree, "/eks_pod_manifests.tf"), re.S
    )[1]
    manifests = evaluate(
        tmp_path,
        f"[for m in {manifests_expression} : yamldecode(yamlencode(m))]",
        values,
    )
    assert [m["kind"] for m in manifests] == ["ServiceAccount", "Role", "RoleBinding"]
    assert all(m["metadata"]["namespace"] == "application" for m in manifests)
    role, binding = manifests[1:]
    assert {r for rule in role["rules"] for r in rule["resources"]} == {
        "configmaps",
        "pods",
        "pods/ephemeralcontainers",
        "pods/exec",
        "deployments",
    }
    assert "*" not in json.dumps(manifests)
    assert [s["kind"] for s in binding["subjects"]] == ["ServiceAccount", "Group"]
    assert (
        binding["subjects"][1]["name"] == values["var.fis_eks_pods"]["kubernetes_group"]
    )
    assert binding["roleRef"]["name"] == role["metadata"]["name"]


@needs_terraform
@pytest.mark.parametrize(
    "index,field,value",
    [
        (0, "role_arn", "arn:aws:iam::999999999999:role/fis"),
        (0, "role_arn", "arn:aws-cn:iam::123456789012:role/fis"),
        (1, "arn", "arn:aws:eks:eu-west-1:123456789012:cluster/application"),
        (1, "name", "*"),
        (2, "authentication_mode", "CONFIG_MAP"),
        (2, "version", "1.29"),
        (2, "version", "bad"),
        (3, "namespace", "kube-system"),
        (3, "namespace", "*"),
        (3, "deployment_name", ""),
        (4, "service_account", "default"),
        (4, "kubernetes_group", "system:masters"),
        (4, "authorized_roles", []),
        (5, "selection_mode", "COUNT(6)"),
        (5, "action_name", "bad/name"),
    ],
)
def test_native_preconditions_reject_unsafe_overrides(tmp_path, index, field, value):
    values = native_values()
    if field in {"role_arn", "action_name"}:
        values[f"var.{field}"] = value
    elif field in values["var.fis_eks_cluster"]:
        values["var.fis_eks_cluster"][field] = value
    else:
        values["var.fis_eks_pods"][field] = value
    assert (
        evaluate(tmp_path, str(eks_fault_preconditions()[index]["condition"]), values)
        is False
    )


@needs_terraform
@pytest.mark.parametrize("selection", SELECTION_MODES)
def test_native_preconditions_accept_supported_selection(tmp_path, selection):
    values = native_values()
    values["var.fis_eks_pods"]["selection_mode"] = selection
    assert (
        evaluate(
            tmp_path,
            " && ".join(f"({p['condition']})" for p in eks_fault_preconditions()),
            values,
        )
        is True
    )


@needs_terraform
@pytest.mark.parametrize(
    "mode", ["valid", "wrong_path", "wrong_account", "config_map", "old_version"]
)
def test_native_access_entries_require_exact_roles_and_ready_authentication(
    tmp_path, mode
):
    native = native_values()
    cluster = native["var.fis_eks_cluster"]
    values = {
        "each.value": {
            "arn": native["var.role_arn"],
            "native_arn": native["var.role_arn"],
        },
        "aws_eks_cluster.target": {
            "arn": cluster["arn"],
            "version": cluster["version"],
            "access_config": [{"authentication_mode": cluster["authentication_mode"]}],
        },
    }
    if mode == "wrong_path":
        values["each.value"]["native_arn"] = native["var.role_arn"].replace(
            "fis/", "other/"
        )
    elif mode == "wrong_account":
        values["each.value"] = {
            k: v.replace("123456789012", "999999999999")
            for k, v in values["each.value"].items()
        }
    elif mode == "config_map":
        values["aws_eks_cluster.target"]["access_config"][0]["authentication_mode"] = (
            "CONFIG_MAP"
        )
    elif mode == "old_version":
        values["aws_eks_cluster.target"]["version"] = "1.29"
    assert evaluate(
        tmp_path,
        " && ".join(
            f"({p['condition']})"
            for p in access_preconditions("aws_eks_cluster.target")
        ),
        values,
    ) is (mode == "valid")


@pytest.mark.terraform
@needs_terraform
@pytest.mark.parametrize(
    "mode",
    [
        "plain",
        "duplicate",
        "all",
        "count",
        "shared_role",
        "distinct_roles",
        "api",
        "regional",
        "observability",
    ],
)
def test_generated_projects_validate_and_have_acyclic_graphs(tmp_path, mode):
    payload = architecture()
    if mode == "duplicate":
        payload["connections"].append(deepcopy(payload["connections"][0]))
    elif mode in {"all", "count"}:
        payload["connections"][0]["connection_config"]["selection_mode"] = (
            "ALL" if mode == "all" else "COUNT(5)"
        )
    elif mode in {"shared_role", "distinct_roles"}:
        add_experiment(payload, shared_role=mode == "shared_role")
    elif mode == "api":
        payload["resources"][1]["config"]["authentication_mode"] = "API"
    elif mode == "regional":
        for instance in payload["resources"]:
            instance["provider_region"] = "eu-west-1"
    elif mode == "observability":
        mixed = prometheus_architecture()
        connect_storage_and_grafana(mixed)
        source = payload["resources"][0]
        mixed["resources"].append(dict(source, name="experiment", id="experiment"))
        mixed["connections"].append(
            dict(
                payload["connections"][0],
                source="experiment",
                source_id="experiment",
                target="source-resource",
                target_id="src",
            )
        )
        mixed["resources"][0]["config"].update(
            cluster_role_arn="arn:aws:iam::123456789012:role/eks/cluster",
            subnet_ids=["subnet-12345678", "subnet-87654321"],
        )
        payload = mixed
    tree = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    _write_tree(tmp_path, tree)
    env = tmp_path / "connection-check/environments/dev"
    _run_terraform([arg for arg in _init_args() if arg != "-backend=false"], env)
    _run_terraform(["validate", "-no-color"], env)
    _run_terraform(["graph", "-type=plan"], env)
