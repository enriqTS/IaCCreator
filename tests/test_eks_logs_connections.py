"""Control-plane logging uses a ready native group without cluster dependency cycles."""

from copy import deepcopy

import hcl2
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.eks_logs import eks_log_preconditions
from app.models.connection_configs.eks_logs import LOG_TYPES, EksLogsConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_eks_prometheus_connections import connect_managed_network, evaluate
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.EKS, ServiceType.CLOUDWATCH, None, {})
    )


def enabled_types(tree):
    parsed = hcl2.loads(
        file_with(tree, "/environments/dev/main.tf"),
        serialization_options=hcl2.utils.SerializationOptions(strip_string_quotes=True),
    )
    return parsed["module"][0]["source-resource"]["enabled_cluster_log_types"]


def test_native_destination_naming_waits_for_group_without_creating_roles():
    payload = architecture()
    tree = generate(payload)
    cluster = resources(tree, "aws_eks_cluster")[0]
    assert cluster["enabled_cluster_log_types"] == "${var.enabled_cluster_log_types}"
    assert len(cluster["lifecycle"][0]["precondition"]) == 4
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    for kind in (
        "aws_iam_role",
        "aws_iam_role_policy",
        "aws_iam_service_linked_role",
        "aws_cloudwatch_log_resource_policy",
        "aws_eks_addon",
    ):
        assert not resources(tree, kind)
    main = file_with(tree, "/environments/dev/main.tf")
    assert (
        "log_group_name = module.source-resource.control_plane_log_group_name" in main
    )
    assert (
        "control_plane_log_group = module.target-resource.eks_control_plane_destination"
        in main
    )
    assert enabled_types(tree) == list(LOG_TYPES)
    outputs = file_with(tree, "/source-resource/outputs.tf")
    assert '"/aws/eks/${var.cluster_name}/cluster"' in outputs
    destination = file_with(tree, "/target-resource/outputs.tf")
    assert "aws_cloudwatch_log_group.target-resource.arn" in destination
    assert "aws_cloudwatch_log_group.target-resource.log_group_class" in destination
    assert "module.source-resource" not in destination
    contribution = ConnectionProcessor().process_all(project(payload))
    assert {(item.module, item.filename) for item in contribution.resources} == {
        ("source-resource", "control_plane_logs.tf")
    }
    assert not contribution.iam


@given(
    name=resource_name_st,
    selected=st.sets(st.sampled_from(LOG_TYPES), min_size=1),
    duplicate=st.booleans(),
)
@settings(max_examples=20, deadline=None)
def test_selected_types_and_duplicate_connections_are_deterministic(
    name, selected, duplicate
):
    payload = architecture()
    payload["resources"][0]["config"]["cluster_name"] = name
    payload["connections"][0]["connection_config"] = {
        kind: kind in selected for kind in LOG_TYPES
    }
    if duplicate:
        payload["connections"].append(deepcopy(payload["connections"][0]))
    tree = generate(payload)
    assert enabled_types(tree) == [kind for kind in LOG_TYPES if kind in selected]
    assert (
        file_with(tree, "/source-resource/variables.tf").count(
            'variable "enabled_cluster_log_types"'
        )
        == 1
    )
    assert len(resources(tree, "aws_cloudwatch_log_group")) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree


@pytest.mark.parametrize("value", ["true", "false", 1, 0, None, [], {}])
def test_log_selection_requires_real_booleans(value):
    with pytest.raises(ValidationError):
        EksLogsConfig(api=value)


def test_empty_and_unknown_log_selections_are_rejected():
    for config in ({kind: False for kind in LOG_TYPES}, {"application": True}):
        with pytest.raises(ValidationError):
            EksLogsConfig.model_validate(config)
        payload = architecture()
        payload["connections"][0]["connection_config"] = config
        with pytest.raises(InvalidConnectionConfigError):
            generate(payload)


@pytest.mark.parametrize(
    "mode", ["two_groups", "shared_group", "conflicting_selection"]
)
def test_conflicting_cluster_group_ownership_or_selections_fail_generation_and_preview(
    mode,
):
    payload = architecture()
    connection = deepcopy(payload["connections"][0])
    if mode == "conflicting_selection":
        connection["connection_config"] = {"api": False}
    else:
        index = 1 if mode == "two_groups" else 0
        resource = deepcopy(payload["resources"][index])
        resource.update(name="other-resource", id="other-resource")
        payload["resources"].append(resource)
        direction = "target" if mode == "two_groups" else "source"
        connection.update(
            {direction: "other-resource", f"{direction}_id": "other-resource"}
        )
    payload["connections"].append(connection)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)
    with pytest.raises(InvalidConnectionConfigError):
        ConnectionPreviewer().preview_all(project(payload))


@pytest.mark.parametrize(
    "config",
    [
        {"log_group_name": "custom-logs"},
        {"log_group_class": "INFREQUENT_ACCESS"},
        {"log_group_class": "DELIVERY"},
        {"kms_key_id": "arn:aws:kms:us-east-1:123456789012:key/example"},
    ],
)
def test_unsupported_destination_settings_are_rejected(config):
    payload = architecture()
    payload["resources"][1]["config"].update(config)
    with pytest.raises(InvalidConnectionConfigError):
        generate(payload)


def test_managed_customer_key_rejected_independently_of_connection_order():
    payload = architecture()
    template = connection_architecture(
        resolve_spec(ServiceType.KMS, ServiceType.CLOUDWATCH, None, {})
    )
    payload["resources"].append(
        dict(template["resources"][0], name="log-key", id="log-key")
    )
    payload["connections"].append(
        dict(template["connections"][0], source="log-key", source_id="log-key")
    )
    for _ in range(2):
        with pytest.raises(InvalidConnectionConfigError, match="service-linked-role"):
            generate(payload)
        payload["connections"].reverse()


def test_matching_manual_name_preserves_retention_tags_and_cluster_configuration():
    payload = architecture()
    payload["resources"][0]["config"].update(
        cluster_name="production", eks_version="1.34", eks_endpoint_public_access=False
    )
    payload["resources"][1]["config"].update(
        log_group_name="/aws/eks/production/cluster",
        retention_in_days=14,
        tags={"Owner": "platform"},
    )
    tree = generate(payload)
    cluster = resources(tree, "aws_eks_cluster")[0]
    assert cluster["version"] == "${var.eks_version}"
    assert (
        cluster["vpc_config"][0]["endpoint_public_access"]
        == "${var.eks_endpoint_public_access}"
    )
    group = resources(tree, "aws_cloudwatch_log_group")[0]
    assert group["retention_in_days"] == "${var.retention_in_days}"
    assert group["tags"] == "${var.tags}"
    assert (
        "log_group_name = module.source-resource.control_plane_log_group_name"
        in file_with(tree, "/environments/dev/main.tf")
    )


def test_region_mismatches_and_environment_region_overrides():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    with pytest.raises(CrossRegionConnectionError):
        generate(payload)
    payload["environments"][0]["variables"]["region"] = "eu-central-1"
    tree = generate(payload)
    assert "providers =" not in file_with(tree, "/environments/dev/main.tf")


def test_unconnected_clusters_keep_logging_unconfigured():
    payload = architecture()
    payload["connections"] = []
    cluster = resources(generate(payload), "aws_eks_cluster")[0]
    assert "enabled_cluster_log_types" not in cluster
    assert "lifecycle" not in cluster


def test_preview_explains_delivery_ownership_and_operational_requirements():
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    assert preview.connection_type == "logs_to"
    assert not preview.iam and not preview.resources
    message = " ".join(issue.message for issue in preview.issues)
    for requirement in (
        "service-linked role",
        "five free IP",
        "best effort",
        "Import",
        "pod/application logs",
        "Customer-managed KMS",
    ):
        assert requirement in message


def native_values():
    return {
        "var.cluster_name": "production",
        "var.enabled_cluster_log_types": list(LOG_TYPES),
        "var.control_plane_log_group": {
            "arn": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/eks/production/cluster",
            "log_group_class": "STANDARD",
            "kms_key_arn": "",
        },
        "data.aws_partition.eks_logs.partition": "aws",
        "data.aws_region.eks_logs.region": "us-east-1",
        "data.aws_caller_identity.eks_logs.account_id": "123456789012",
    }


@needs_terraform
@pytest.mark.parametrize(
    "index,mutation",
    [
        (0, {"cluster_name": "invalid/name"}),
        (0, {"cluster_name": "a" * 101}),
        (1, {"arn": "arn:aws:logs:us-east-1:123456789012:log-group:custom"}),
        (
            1,
            {
                "arn": "arn:aws:logs:eu-west-1:123456789012:log-group:/aws/eks/production/cluster"
            },
        ),
        (
            1,
            {
                "arn": "arn:aws:logs:us-east-1:999999999999:log-group:/aws/eks/production/cluster"
            },
        ),
        (
            1,
            {
                "arn": "arn:aws-cn:logs:us-east-1:123456789012:log-group:/aws/eks/production/cluster"
            },
        ),
        (2, {"log_group_class": "INFREQUENT_ACCESS"}),
        (2, {"kms_key_arn": "arn:aws:kms:us-east-1:123456789012:key/example"}),
        (3, {"enabled_cluster_log_types": []}),
        (3, {"enabled_cluster_log_types": ["audit", "audit"]}),
        (3, {"enabled_cluster_log_types": ["application"]}),
    ],
)
def test_native_guards_reject_unsafe_module_overrides(tmp_path, index, mutation):
    values = native_values()
    for key, value in mutation.items():
        if f"var.{key}" in values:
            values[f"var.{key}"] = value
        else:
            values["var.control_plane_log_group"][key] = value
    assert (
        evaluate(tmp_path, str(eks_log_preconditions()[index]["condition"]), values)
        is False
    )


@needs_terraform
@pytest.mark.parametrize("suffix", ["", ":*"])
def test_native_guards_accept_ready_standard_destinations(tmp_path, suffix):
    values = native_values()
    values["var.control_plane_log_group"]["arn"] += suffix
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in eks_log_preconditions())
        + "]"
    )
    assert evaluate(tmp_path, expression, values) == [True] * 4


def connect_observability_and_storage(payload):
    for service, source in (
        (ServiceType.MANAGED_PROMETHEUS, False),
        (ServiceType.EFS, True),
        (ServiceType.MANAGED_GRAFANA, True),
    ):
        if service == ServiceType.MANAGED_GRAFANA:
            template = connection_architecture(
                resolve_spec(service, ServiceType.CLOUDWATCH, None, {})
            )
        else:
            template = connection_architecture(
                resolve_spec(
                    service if source else ServiceType.EKS,
                    ServiceType.EKS if source else service,
                    None,
                    {},
                )
            )
        name = service.value
        payload["resources"].append(
            dict(template["resources"][0 if source else 1], name=name, id=name)
        )
        payload["connections"].append(
            dict(
                template["connections"][0],
                source=name if source else "source-resource",
                source_id=name if source else "src",
                target="target-resource"
                if service == ServiceType.MANAGED_GRAFANA
                else "source-resource"
                if source
                else name,
                target_id="tgt"
                if service == ServiceType.MANAGED_GRAFANA
                else "src"
                if source
                else name,
            )
        )


@pytest.mark.terraform
@needs_terraform
@pytest.mark.parametrize(
    "mode",
    [
        "plain",
        "audit_only",
        "duplicates",
        "multiple_clusters",
        "mixed",
        "managed_network",
        "regional",
    ],
)
def test_generated_logging_projects_validate_and_have_acyclic_graphs(tmp_path, mode):
    payload = architecture()
    if mode == "audit_only":
        payload["connections"][0]["connection_config"] = {
            kind: kind == "audit" for kind in LOG_TYPES
        }
    elif mode == "duplicates":
        payload["connections"].append(deepcopy(payload["connections"][0]))
    elif mode == "multiple_clusters":
        for index, name in enumerate(["other-cluster", "other-logs"]):
            resource = deepcopy(payload["resources"][index])
            resource.update(name=name, id=name)
            if index == 0:
                resource["config"]["cluster_name"] = "other-cluster"
            payload["resources"].append(resource)
        payload["connections"].append(
            dict(
                payload["connections"][0],
                source="other-cluster",
                source_id="other-cluster",
                target="other-logs",
                target_id="other-logs",
            )
        )
    elif mode == "mixed":
        connect_observability_and_storage(payload)
    elif mode == "managed_network":
        connect_managed_network(payload)
    elif mode == "regional":
        for resource in payload["resources"]:
            resource["provider_region"] = "eu-west-1"
    tree = generate(payload)
    if mode == "mixed":
        assert len(resources(tree, "aws_eks_addon")) == 1
        assert len(resources(tree, "aws_prometheus_scraper")) == 1
        assert len(resources(tree, "aws_grafana_workspace")) == 1
    payload["connections"].reverse()
    assert generate(payload) == tree
    _write_tree(tmp_path, tree)
    env_dir = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], env_dir.parent
    )
    _run_terraform(["validate", "-no-color"], env_dir.parent)
    _run_terraform(["graph", "-type=plan"], env_dir.parent)
