import json
import re
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.codecommit_codebuild import repository_source_preconditions
from app.models.connection_configs.codecommit_codebuild import CodeCommitBuildConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from app.services.service_catalog import build_service_catalog
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_codebuild_logs_connections import add_logs
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
        resolve_spec(ServiceType.CODECOMMIT, ServiceType.CODEBUILD, None, {})
    )


def add_secret(payload):
    template = connection_architecture(
        resolve_spec(ServiceType.CODEBUILD, ServiceType.SECRETS_MANAGER, None, {})
    )
    payload["resources"].append(
        dict(template["resources"][1], name="build-secret", id="build-secret")
    )
    payload["connections"].append(
        dict(
            template["connections"][0],
            source="target-resource",
            source_id="tgt",
            target="build-secret",
            target_id="build-secret",
            connection_config={"environment_name": "PASSWORD"},
        )
    )


def test_native_source_and_scoped_external_role_policy():
    tree = generate(architecture())
    build = resources(tree, "aws_codebuild_project")[0]
    source = build["source"][0]
    assert source["type"] == "${var.source_type}"
    assert source["location"] == "${var.repository_source.clone_url}"
    assert source["buildspec"] == "${var.buildspec}"
    assert source["git_clone_depth"] == "${var.repository_source.git_clone_depth}"
    assert source["git_submodules_config"][0]["fetch_submodules"] is False
    assert source["insecure_ssl"] is False
    assert build["source_version"] == "${var.repository_source.source_version}"
    assert build["service_role"] == "${var.service_role}"
    assert build["depends_on"] == ["${aws_iam_role_policy.repository_source}"]
    assert len(build["lifecycle"][0]["precondition"]) == 6
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert policy["role"] == "${data.aws_iam_role.repository_source.name}"
    assert len(policy["lifecycle"][0]["precondition"]) == 7
    all_text = "\n".join(tree.values())
    assert "module.source-resource.clone_url_http" in all_text
    assert "module.source-resource.repository_arn" in all_text
    assert "module.source-resource.repository_name" in all_text
    assert "aws_codecommit_repository.source-resource.repository_name" in file_with(
        tree, "/source-resource/outputs.tf"
    )
    assert '"codecommit:GitPull"' in all_text and "GitPush" not in all_text
    assert not resources(tree, "aws_iam_role") and not resources(
        tree, "aws_codebuild_webhook"
    )
    contribution = ConnectionProcessor().process_all(project(architecture()))
    assert not contribution.iam
    assert {item.module for item in contribution.resources} == {"target-resource"}
    assert ConnectionPreviewer().preview_all(project(architecture()))[0].issues
    codecommit = build_service_catalog()[ServiceType.CODECOMMIT]
    assert (
        codecommit.lifecycle.value == "retired" and not codecommit.capabilities.diagram
    )
    assert codecommit.capabilities.connectable


@given(
    name=resource_name_st,
    revision=st.one_of(
        st.sampled_from(["main", "release/v1.2", "refs/tags/v2", "a" * 40]),
        resource_name_st.map(lambda name: f"feature/{name}"),
    ),
    depth=st.integers(0, 25),
    duplicates=st.integers(1, 4),
)
@settings(max_examples=25, deadline=None)
def test_property_names_settings_sharing_and_duplicate_order(
    name, revision, depth, duplicates
):
    payload = architecture()
    payload["resources"][0]["name"] = "repository-" + name
    payload["connections"][0].update(
        source=payload["resources"][0]["name"],
        connection_config={"source_version": revision, "git_clone_depth": depth},
    )
    other = deepcopy(payload["resources"][1])
    other.update(name="second-build", id="second-build")
    payload["resources"].append(other)
    payload["connections"].append(
        dict(payload["connections"][0], target="second-build", target_id="second-build")
    )
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * duplicates))
    assert generate(payload) == expected
    assert len(resources(expected, "aws_codecommit_repository")) == 1
    assert len(resources(expected, "aws_iam_role_policy")) == 2


@pytest.mark.parametrize(
    "value",
    [
        "",
        "../main",
        "main..next",
        "main/",
        "main.",
        "main//next",
        "main/.hidden",
        "main.lock",
        "refs/branch.lock/main",
        "main@{1}",
        "a b",
        "${branch}",
        "main\n",
        "a" * 257,
        123,
        True,
        None,
    ],
)
def test_invalid_revision(value):
    with pytest.raises(ValidationError):
        CodeCommitBuildConfig(source_version=value)


@pytest.mark.parametrize("value", [-1, 26, 1.5, "1", True, None])
def test_invalid_depth(value):
    with pytest.raises(ValidationError):
        CodeCommitBuildConfig(git_clone_depth=value)


@pytest.mark.parametrize(
    "case",
    [
        "two-repositories",
        "revision-conflict",
        "depth-conflict",
        "source-type",
        "missing-role",
        "malformed-role",
        "region",
        "environment-region",
    ],
)
def test_conflicts_and_invalid_configuration(case):
    payload = architecture()
    if case == "two-repositories":
        other = dict(payload["resources"][0], name="other-repository", id="other")
        payload["resources"].append(other)
        payload["connections"].append(
            dict(
                payload["connections"][0], source="other-repository", source_id="other"
            )
        )
    elif case in {"revision-conflict", "depth-conflict"}:
        payload["connections"].append(
            dict(
                payload["connections"][0],
                connection_config={"source_version": "next"}
                if case == "revision-conflict"
                else {"git_clone_depth": 0},
            )
        )
    elif case == "source-type":
        payload["resources"][1]["config"]["source_type"] = "CODEPIPELINE"
    elif case == "missing-role":
        payload["resources"][1]["config"]["service_role"] = None
    elif case == "malformed-role":
        payload["resources"][1]["config"]["service_role"] = (
            "arn:aws:iam::123456789012:policy/build"
        )
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


def test_environment_override_can_align_regions_and_unconnected_build_is_unchanged():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    payload["environments"][0]["variables"]["region"] = "us-west-2"
    generate(payload)
    payload["connections"] = []
    tree = generate(payload)
    build = resources(tree, "aws_codebuild_project")[0]
    assert "location" not in build["source"][0]
    assert "source_version" not in build
    assert not resources(tree, "aws_iam_role_policy")


@pytest.mark.parametrize("source_type", [None, "NO_SOURCE", "CODECOMMIT"])
def test_managed_source_accepts_placeholders_and_preserves_explicit_buildspec(
    source_type,
):
    payload = architecture()
    payload["resources"][1]["config"].update(
        source_type=source_type, buildspec="buildspec.yml"
    )
    tree = generate(payload)
    assert '"buildspec.yml"' in "\n".join(tree.values())
    assert '"CODECOMMIT"' in "\n".join(tree.values())
    assert (
        resources(tree, "aws_codebuild_project")[0]["source"][0]["buildspec"]
        == "${var.buildspec}"
    )


def native_values():
    return {
        "var.service_role": "arn:aws:iam::123456789012:role/build/service-role",
        "var.source_type": "CODECOMMIT",
        "var.repository_source": {
            "name": "application",
            "arn": "arn:aws:codecommit:us-east-1:123456789012:application",
            "clone_url": "https://git-codecommit.us-east-1.amazonaws.com/v1/repos/application",
            "source_version": "main",
            "git_clone_depth": 1,
        },
        "data.aws_partition.repository_source.partition": "aws",
        "data.aws_partition.repository_source.dns_suffix": "amazonaws.com",
        "data.aws_region.repository_source.region": "us-east-1",
        "data.aws_caller_identity.repository_source.account_id": "123456789012",
        "data.aws_iam_role.repository_source.arn": "arn:aws:iam::123456789012:role/build/service-role",
    }


@needs_terraform
@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "arn-account",
        "arn-region",
        "arn-partition",
        "arn-name",
        "url",
        "role-account",
        "role-path",
        "source-type",
        "revision",
        "depth",
        "fraction",
        "gov",
        "china",
    ],
)
def test_native_guards_and_scoped_policy(tmp_path, case):
    values = native_values()
    repository = values["var.repository_source"]
    if case.startswith("arn-"):
        original, replacement = {
            "arn-account": ("123456789012", "111111111111"),
            "arn-region": ("us-east-1", "eu-west-1"),
            "arn-partition": ("arn:aws:", "arn:aws-cn:"),
            "arn-name": ("application", "other"),
        }[case]
        repository["arn"] = repository["arn"].replace(original, replacement)
    elif case == "url":
        repository["clone_url"] = repository["clone_url"].replace(
            "application", "other"
        )
    elif case == "role-account":
        values["var.service_role"] = values["var.service_role"].replace(
            "123456789012", "111111111111"
        )
    elif case == "role-path":
        values["data.aws_iam_role.repository_source.arn"] = values[
            "var.service_role"
        ].replace("build/", "other/")
    elif case == "source-type":
        values["var.source_type"] = "NO_SOURCE"
    elif case == "revision":
        repository["source_version"] = "refs/branch.lock/main"
    elif case == "depth":
        repository["git_clone_depth"] = 26
    elif case == "fraction":
        repository["git_clone_depth"] = 1.5
    elif case in {"gov", "china"}:
        partition, region, suffix = (
            ("aws-us-gov", "us-gov-west-1", "amazonaws.com")
            if case == "gov"
            else ("aws-cn", "cn-north-1", "amazonaws.com.cn")
        )
        values["data.aws_partition.repository_source.partition"] = partition
        values["data.aws_partition.repository_source.dns_suffix"] = suffix
        values["data.aws_region.repository_source.region"] = region
        repository["arn"] = (
            f"arn:{partition}:codecommit:{region}:123456789012:application"
        )
        repository["clone_url"] = (
            f"https://git-codecommit.{region}.{suffix}/v1/repos/application"
        )
        values["var.service_role"] = values[
            "data.aws_iam_role.repository_source.arn"
        ] = f"arn:{partition}:iam::123456789012:role/build/service-role"
    conditions = [item["condition"] for item in repository_source_preconditions()] + [
        "data.aws_iam_role.repository_source.arn == var.service_role"
    ]
    assert evaluate(tmp_path, "alltrue([" + ", ".join(conditions) + "])", values) is (
        case in {"valid", "gov", "china"}
    )
    if case == "valid":
        text = file_with(generate(architecture()), "/repository_source.tf")
        expression = re.search(r"  policy = (.*?)\n  lifecycle \{", text, re.S)[1]
        policy = json.loads(evaluate(tmp_path, expression, values))
        assert policy["Statement"] == [
            {
                "Effect": "Allow",
                "Action": ["codecommit:GitPull"],
                "Resource": repository["arn"],
            }
        ]


@pytest.mark.terraform
@needs_terraform
@pytest.mark.parametrize(
    "mode",
    [
        "plain",
        "full-history",
        "tag",
        "commit",
        "duplicates",
        "shared-role",
        "regional",
        "logs-secrets",
        "eventbridge",
    ],
)
def test_projects_validate_with_acyclic_graphs(tmp_path, mode):
    payload = architecture()
    if mode == "full-history":
        payload["connections"][0]["connection_config"] = {"git_clone_depth": 0}
    elif mode in {"tag", "commit"}:
        payload["connections"][0]["connection_config"] = {
            "source_version": "refs/tags/v1" if mode == "tag" else "a" * 40
        }
    elif mode == "duplicates":
        payload["connections"] *= 3
    elif mode == "shared-role":
        payload["resources"].append(
            dict(payload["resources"][1], name="second-build", id="second")
        )
        payload["connections"].append(
            dict(payload["connections"][0], target="second-build", target_id="second")
        )
    elif mode == "regional":
        payload["environments"][0]["variables"]["region"] = "us-west-2"
    elif mode == "logs-secrets":
        add_logs(payload, "target-resource", "tgt")
        add_secret(payload)
    elif mode == "eventbridge":
        template = connection_architecture(
            resolve_spec(ServiceType.EVENTBRIDGE, ServiceType.CODEBUILD, None, {})
        )
        payload["resources"].append(
            dict(template["resources"][0], name="build-rule", id="rule")
        )
        payload["connections"].append(
            dict(template["connections"][0], source="build-rule", source_id="rule")
        )
    tree = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    if mode == "logs-secrets":
        build = resources(tree, "aws_codebuild_project")[0]
        assert set(build["depends_on"]) == {
            "${aws_iam_role_policy.runtime_secrets}",
            "${aws_iam_role_policy.build_logs}",
            "${aws_iam_role_policy.repository_source}",
        }
        assert len(build["lifecycle"][0]["precondition"]) == 11
        assert 'type = "SECRETS_MANAGER"' in file_with(
            tree, "/target-resource/codebuild.tf"
        )
    _write_tree(tmp_path, tree)
    root = tmp_path / "connection-check" / "environments" / "dev"
    _run_terraform(
        [argument for argument in _init_args() if argument != "-backend=false"], root
    )
    _run_terraform(["validate", "-no-color"], root)
    _run_terraform(["graph", "-type=plan"], root)
