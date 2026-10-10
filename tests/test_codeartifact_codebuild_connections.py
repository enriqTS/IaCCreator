import json
import re
from copy import deepcopy

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.codeartifact_codebuild import package_source_preconditions
from app.models.connection_configs.codeartifact_codebuild import CodeArtifactBuildConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_codebuild_logs_connections import add_logs
from tests.test_codecommit_codebuild_connections import add_secret
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
        resolve_spec(ServiceType.CODEARTIFACT, ServiceType.CODEBUILD, None, {})
    )


def configured_buildspec():
    return {
        "version": 0.2,
        "env": {
            "variables": {"MODE": "release", "LITERAL": "${value}"},
            "shell": "bash",
        },
        "phases": {
            "install": {
                "runtime-versions": {"nodejs": 20},
                "commands": ["echo install"],
            },
            "pre_build": {
                "commands": ["echo first", "echo second"],
                "finally": ["echo cleanup"],
                "on-failure": "ABORT",
            },
            "build": {"commands": ["echo build"], "finally": ["echo end"]},
            "post_build": {"commands": ["echo done"]},
        },
        "artifacts": {"files": ["dist/**/*"]},
        "cache": {"paths": ["node_modules/**/*"]},
        "reports": {"tests": {"files": ["test.xml"], "file-format": "JUNITXML"}},
    }


def test_native_package_source_external_role_and_runtime_authentication():
    payload = architecture()
    ir = project(payload)
    config = next(
        instance.config
        for module in ir.modules
        for instance in module.instances
        if instance.name == "target-resource"
    )
    original = config.buildspec
    previews = ConnectionPreviewer().preview_all(ir)
    assert config.buildspec == original
    assert previews[0].resources[0].module == "target-resource"
    assert any(
        "publishing is not granted" in issue.message for issue in previews[0].issues
    )
    tree = generate(payload)
    text = "\n".join(tree.values())
    for name in (
        "domain_arn",
        "domain_name",
        "owner",
        "repository_arn",
        "repository_name",
    ):
        assert f"module.source-resource.{name}" in text
    build = resources(tree, "aws_codebuild_project")[0]
    assert build["source"][0]["buildspec"] == "${local.package_login_buildspec}"
    assert build["depends_on"] == ["${aws_iam_role_policy.package_source}"]
    assert len(build["lifecycle"][0]["precondition"]) == 5
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert policy["role"] == "${data.aws_iam_role.package_source.name}"
    assert len(policy["lifecycle"][0]["precondition"]) == 6
    assert "--duration-seconds 0" in text
    assert "PublishPackageVersion" not in text
    assert not resources(tree, "aws_iam_role")
    assert 'data "aws_codeartifact_authorization_token"' not in text
    assert "authorization_token" not in text


@given(
    name=resource_name_st,
    tool=st.sampled_from(["npm", "pip"]),
    duplicates=st.integers(1, 4),
)
@settings(max_examples=20, deadline=None)
def test_property_named_repositories_shared_roles_and_duplicate_order(
    name, tool, duplicates
):
    payload = architecture()
    payload["resources"][0]["config"].update(
        domain_name="domain-" + name + "0", repository_name="packages-" + name
    )
    payload["connections"][0]["connection_config"] = {"tool": tool}
    other = deepcopy(payload["resources"][1])
    other.update(name="second-build", id="second")
    payload["resources"].append(other)
    payload["connections"].append(
        dict(payload["connections"][0], target="second-build", target_id="second")
    )
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * duplicates))
    assert generate(payload) == expected
    assert len(resources(expected, "aws_codeartifact_repository")) == 1
    assert len(resources(expected, "aws_iam_role_policy")) == 2


@pytest.mark.parametrize("value", ["maven", "twine", "", "${tool}", True, 123, None])
def test_invalid_tool(value):
    with pytest.raises(ValidationError):
        CodeArtifactBuildConfig(tool=value)


@pytest.mark.parametrize(
    "buildspec",
    [
        "buildspec.yml",
        "",
        "[]",
        "version: 0.1",
        "version: 0.2\nphases: []",
        "version: 0.2\nphases:\n  pre_build: null",
        "version: 0.2\nphases:\n  pre_build:\n    commands: echo hello",
        "version: 0.2\nphases:\n  pre_build:\n    commands: [true]",
        "version: 0.2\nphases:\n  pre_build:\n    commands: [{echo: bad}]",
        "version: 0.2\nphases:\n  pre_build:\n    commands: null",
        "version: [broken",
        "version: 0.2\nvalue: .nan",
        "version: 0.2\nvalue: &a [*a]",
    ],
)
def test_incompatible_inline_buildspecs_are_rejected(buildspec):
    payload = architecture()
    payload["resources"][1]["config"]["buildspec"] = buildspec
    with pytest.raises(InvalidConnectionConfigError, match="buildspec|pre_build"):
        generate(payload)


@pytest.mark.parametrize(
    "case",
    [
        "two-repositories",
        "tool-conflict",
        "missing-role",
        "bad-role",
        "domain",
        "repository",
        "region",
        "environment-region",
    ],
)
def test_conflicts_and_invalid_identity(case):
    payload = architecture()
    if case == "two-repositories":
        payload["resources"].append(
            dict(payload["resources"][0], name="other-packages", id="other")
        )
        payload["connections"].append(
            dict(payload["connections"][0], source="other-packages", source_id="other")
        )
    elif case == "tool-conflict":
        payload["connections"].append(
            dict(payload["connections"][0], connection_config={"tool": "pip"})
        )
    elif case in {"missing-role", "bad-role"}:
        payload["resources"][1]["config"]["service_role"] = (
            None if case == "missing-role" else "arn:aws:iam::123456789012:policy/build"
        )
    elif case in {"domain", "repository"}:
        payload["resources"][0]["config"][
            "domain_name" if case == "domain" else "repository_name"
        ] = "$(danger)"
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


def test_unconnected_build_unchanged_and_environment_can_align_regions():
    payload = architecture()
    payload["resources"][0]["provider_region"] = "eu-west-1"
    payload["environments"][0]["variables"]["region"] = "us-west-2"
    generate(payload)
    payload["connections"] = []
    tree = generate(payload)
    assert (
        resources(tree, "aws_codebuild_project")[0]["source"][0]["buildspec"]
        == "${var.buildspec}"
    )
    assert not resources(tree, "aws_iam_role_policy")
    assert "var.package_source" not in "\n".join(tree.values())


def native_values():
    return {
        "var.service_role": "arn:aws:iam::123456789012:role/build/service-role",
        "var.package_source": {
            "domain_name": "application",
            "domain_arn": "arn:aws:codeartifact:us-east-1:123456789012:domain/application",
            "owner": "123456789012",
            "repository_name": "packages",
            "repository_arn": "arn:aws:codeartifact:us-east-1:123456789012:repository/application/packages",
            "tool": "npm",
        },
        "local.package_buildspec": configured_buildspec(),
        "data.aws_partition.package_source.partition": "aws",
        "data.aws_region.package_source.region": "us-east-1",
        "data.aws_caller_identity.package_source.account_id": "123456789012",
        "data.aws_iam_role.package_source.arn": "arn:aws:iam::123456789012:role/build/service-role",
    }


@needs_terraform
@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "domain-account",
        "domain-region",
        "repository-domain",
        "repository-region",
        "owner",
        "domain-injection",
        "repository-injection",
        "role-account",
        "role-path",
        "tool",
        "version",
        "phase",
        "commands",
        "numeric-command",
        "gov",
        "china",
    ],
)
def test_native_guards_and_emitted_policy(tmp_path, case):
    values = native_values()
    source = values["var.package_source"]
    if case in {
        "domain-account",
        "domain-region",
        "repository-domain",
        "repository-region",
    }:
        field, original, replacement = {
            "domain-account": ("domain_arn", "123456789012", "111111111111"),
            "domain-region": ("domain_arn", "us-east-1", "eu-west-1"),
            "repository-domain": ("repository_arn", "application", "other"),
            "repository-region": ("repository_arn", "us-east-1", "eu-west-1"),
        }[case]
        source[field] = source[field].replace(original, replacement)
    elif case == "owner":
        source["owner"] = "111111111111"
    elif case in {"domain-injection", "repository-injection"}:
        source["domain_name" if case == "domain-injection" else "repository_name"] = (
            "$(danger)"
        )
    elif case == "role-account":
        values["var.service_role"] = values["var.service_role"].replace(
            "123456789012", "111111111111"
        )
    elif case == "role-path":
        values["data.aws_iam_role.package_source.arn"] = values[
            "var.service_role"
        ].replace("build/", "other/")
    elif case == "tool":
        source["tool"] = "other"
    elif case == "version":
        values["local.package_buildspec"]["version"] = 0.1
    elif case == "phase":
        values["local.package_buildspec"]["phases"]["pre_build"] = None
    elif case in {"commands", "numeric-command"}:
        values["local.package_buildspec"]["phases"]["pre_build"]["commands"] = (
            "echo bad" if case == "commands" else [123]
        )
    elif case in {"gov", "china"}:
        partition, region = (
            ("aws-us-gov", "us-gov-west-1")
            if case == "gov"
            else ("aws-cn", "cn-north-1")
        )
        values["data.aws_partition.package_source.partition"] = partition
        values["data.aws_region.package_source.region"] = region
        source["domain_arn"] = (
            f"arn:{partition}:codeartifact:{region}:123456789012:domain/application"
        )
        source["repository_arn"] = (
            f"arn:{partition}:codeartifact:{region}:123456789012:repository/application/packages"
        )
        values["var.service_role"] = values["data.aws_iam_role.package_source.arn"] = (
            f"arn:{partition}:iam::123456789012:role/build/service-role"
        )
    conditions = [item["condition"] for item in package_source_preconditions()] + [
        "data.aws_iam_role.package_source.arn == var.service_role"
    ]
    assert evaluate(tmp_path, "alltrue([" + ", ".join(conditions) + "])", values) is (
        case in {"valid", "gov", "china"}
    )
    if case == "valid":
        text = file_with(generate(architecture()), "/package_source.tf")
        expression = re.search(r"  policy = (.*?)\n  lifecycle \{", text, re.S)[1]
        policy = json.loads(evaluate(tmp_path, expression, values))
        assert policy["Statement"] == [
            {
                "Effect": "Allow",
                "Action": ["codeartifact:GetAuthorizationToken"],
                "Resource": source["domain_arn"],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "codeartifact:GetRepositoryEndpoint",
                    "codeartifact:ReadFromRepository",
                ],
                "Resource": source["repository_arn"],
            },
            {
                "Effect": "Allow",
                "Action": ["sts:GetServiceBearerToken"],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {"sts:AWSServiceName": "codeartifact.amazonaws.com"}
                },
            },
        ]


@needs_terraform
@pytest.mark.parametrize(
    "tool,variant",
    [
        ("npm", "complete"),
        ("pip", "complete"),
        ("npm", "no-prebuild"),
        ("pip", "no-phases"),
        ("npm", "empty-commands"),
    ],
)
def test_generated_buildspec_preserves_settings_and_logs_in_first(
    tmp_path, tool, variant
):
    payload = architecture()
    payload["connections"][0]["connection_config"] = {"tool": tool}
    original = configured_buildspec()
    if variant == "no-prebuild":
        original["phases"].pop("pre_build")
    elif variant == "no-phases":
        original.pop("phases")
    elif variant == "empty-commands":
        original["phases"]["pre_build"]["commands"] = []
    payload["resources"][1]["config"]["buildspec"] = yaml.safe_dump(original)
    tree = generate(payload)
    text = file_with(tree, "/package_source.tf")
    values = native_values()
    values["var.package_source"]["tool"] = tool
    values["var.buildspec"] = payload["resources"][1]["config"]["buildspec"]
    for name in (
        "package_buildspec",
        "package_login_command",
        "package_login_buildspec",
    ):
        expression = re.search(rf"  {name} = (.*)", text)[1]
        values[f"local.{name}"] = evaluate(tmp_path, expression, values)
    result = yaml.safe_load(values["local.package_login_buildspec"])
    command = result["phases"]["pre_build"]["commands"].pop(0)
    assert (
        command
        == f"aws codeartifact login --tool {tool} --domain application --domain-owner 123456789012 --repository packages --region us-east-1 --duration-seconds 0"
    )
    expected = deepcopy(original)
    expected.setdefault("phases", {}).setdefault("pre_build", {}).setdefault(
        "commands", []
    )
    assert result == expected


def add_repository(payload):
    template = connection_architecture(
        resolve_spec(ServiceType.CODECOMMIT, ServiceType.CODEBUILD, None, {})
    )
    payload["resources"].append(
        dict(template["resources"][0], name="source-repository", id="repo")
    )
    payload["connections"].append(
        dict(template["connections"][0], source="source-repository", source_id="repo")
    )


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode",
    [
        "npm",
        "pip",
        "duplicates",
        "regional",
        "shared-role",
        "codecommit",
        "logs-secrets",
        "all",
        "encrypted-domain",
        "upstream",
    ],
)
def test_provider_validation_and_acyclic_composition(tmp_path, mode):
    payload = architecture()
    if mode == "pip":
        payload["connections"][0]["connection_config"] = {"tool": "pip"}
    elif mode == "duplicates":
        payload["connections"] *= 3
    elif mode == "regional":
        payload["environments"][0]["variables"]["region"] = "us-west-2"
    elif mode == "shared-role":
        payload["resources"].append(
            dict(payload["resources"][1], name="second-build", id="second")
        )
        payload["connections"].append(
            dict(payload["connections"][0], target="second-build", target_id="second")
        )
    elif mode == "encrypted-domain":
        payload["resources"].append(
            {
                "name": "domain-key",
                "id": "key",
                "service_type": "kms",
                "config": {"description": "Package domain encryption"},
            }
        )
        payload["connections"].append(
            {
                "source": "domain-key",
                "target": "source-resource",
                "connection_type": "encrypts",
            }
        )
    elif mode == "upstream":
        payload["resources"][0]["config"]["upstream_repository_names"] = [
            "external-packages"
        ]
    if mode in {"codecommit", "all"}:
        add_repository(payload)
    if mode in {"logs-secrets", "all"}:
        add_logs(payload, "target-resource", "tgt")
        add_secret(payload)
    tree = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    if mode == "all":
        build = resources(tree, "aws_codebuild_project")[0]
        assert set(build["depends_on"]) == {
            "${aws_iam_role_policy.package_source}",
            "${aws_iam_role_policy.repository_source}",
            "${aws_iam_role_policy.runtime_secrets}",
            "${aws_iam_role_policy.build_logs}",
        }
        assert len(build["lifecycle"][0]["precondition"]) == 16
        assert build["source"][0]["location"] == "${var.repository_source.clone_url}"
        assert build["source"][0]["buildspec"] == "${local.package_login_buildspec}"
        assert 'dynamic "environment_variable"' in file_with(tree, "/codebuild.tf")
    _write_tree(tmp_path, tree)
    environment = tmp_path / "connection-check/environments/dev"
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], environment
    )
    _run_terraform(["validate", "-no-color"], environment)
    _run_terraform(["graph", "-type=plan"], environment)
