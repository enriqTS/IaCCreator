import json
import re
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.codecommit_codepipeline import pipeline_source_policy_preconditions
from app.models.connection_configs.codecommit_codepipeline import (
    CodeCommitPipelineConfig,
)
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.service_catalog import build_service_catalog
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
        resolve_spec(ServiceType.CODECOMMIT, ServiceType.CODEPIPELINE, None, {})
    )


def change_stages(payload, update):
    config = payload["resources"][1]["config"]
    stages = json.loads(config["stages_json"])
    update(stages)
    config["stages_json"] = json.dumps(stages)


def add_artifacts(payload, encrypted=False):
    template = connection_architecture(
        resolve_spec(ServiceType.CODEPIPELINE, ServiceType.S3, "stores_artifacts", {})
    )
    payload["resources"][1]["config"].pop("artifact_bucket_name", None)
    payload["resources"].append(
        dict(template["resources"][1], name="artifacts", id="artifacts")
    )
    payload["connections"].append(
        dict(
            template["connections"][0],
            source="target-resource",
            source_id="tgt",
            target="artifacts",
            target_id="artifacts",
        )
    )
    if encrypted:
        payload["resources"].append(
            {
                "name": "artifact-key",
                "id": "artifact-key",
                "service_type": "kms",
                "config": {"description": "Pipeline artifacts"},
            }
        )
        payload["connections"].append(
            {
                "source": "artifact-key",
                "target": "artifacts",
                "connection_type": "encrypts",
            }
        )


def test_native_binding_preserves_stages_and_scopes_permissions():
    payload = architecture()
    ir = project(payload)
    pipeline_config = next(
        instance.config
        for module in ir.modules
        for instance in module.instances
        if instance.name == "target-resource"
    )
    original_stages = pipeline_config.stages_json
    previews = ConnectionPreviewer().preview_all(ir)
    assert pipeline_config.stages_json == original_stages
    assert any(
        "automatically starts an execution" in issue.message
        for issue in previews[0].issues
    )
    assert [resource.resource_type for resource in previews[0].resources] == [
        "aws_iam_role_policy"
    ]
    tree = generate(payload)
    text = "\n".join(tree.values())
    assert "module.source-resource.repository_name" in text
    assert "module.source-resource.repository_arn" in text
    pipeline = resources(tree, "aws_codepipeline")[0]
    assert pipeline["depends_on"] == ["${aws_iam_role_policy.repository_source}"]
    assert len(pipeline["lifecycle"][0]["precondition"]) == 8
    policy = resources(tree, "aws_iam_role_policy")[0]
    assert policy["role"] == "${data.aws_iam_role.repository_source.name}"
    assert len(policy["lifecycle"][0]["precondition"]) == 9
    assert 'PollForSourceChanges = "false"' in text
    assert 'OutputArtifactFormat = "CODE_ZIP"' in text
    assert "codecommit:GitPull" not in text
    assert not resources(tree, "aws_cloudwatch_event_rule")
    codecommit = build_service_catalog()[ServiceType.CODECOMMIT]
    assert (
        codecommit.lifecycle.value == "retired" and not codecommit.capabilities.diagram
    )


@given(
    name=resource_name_st,
    branch=resource_name_st.map(lambda name: "feature/" + name),
    duplicates=st.integers(1, 4),
)
@settings(max_examples=20, deadline=None)
def test_property_selected_names_shared_roles_and_duplicate_order(
    name, branch, duplicates
):
    payload = architecture()
    request = {
        "stage_name": "Stage-" + name,
        "action_name": "Action-" + name,
        "branch_name": branch,
    }
    change_stages(
        payload,
        lambda stages: (
            stages[0].update(name=request["stage_name"]),
            stages[0]["actions"][0].update(name=request["action_name"]),
        ),
    )
    payload["connections"][0]["connection_config"] = request
    other = deepcopy(payload["resources"][1])
    other.update(name="second-pipeline", id="second")
    payload["resources"].append(other)
    payload["connections"].append(
        dict(payload["connections"][0], target="second-pipeline", target_id="second")
    )
    expected = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * duplicates))
    assert generate(payload) == expected
    assert len(resources(expected, "aws_codecommit_repository")) == 1
    assert len(resources(expected, "aws_iam_role_policy")) == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("branch_name", "main..next"),
        ("branch_name", "main//next"),
        ("branch_name", "main.lock"),
        ("branch_name", "branch/.hidden"),
        ("branch_name", "main/"),
        ("branch_name", "main."),
        ("branch_name", "${branch}"),
        ("branch_name", "main\n"),
        ("branch_name", 123),
        ("branch_name", "a" * 257),
        ("stage_name", ""),
        ("stage_name", "a b"),
        ("action_name", "a" * 101),
        ("action_name", True),
        ("stage_name", None),
    ],
)
def test_invalid_config(field, value):
    with pytest.raises(ValidationError):
        CodeCommitPipelineConfig.model_validate({field: value})


@pytest.mark.parametrize(
    "case",
    [
        "two-repositories",
        "branch-conflict",
        "action-conflict",
        "missing-role",
        "bad-role",
        "missing-store",
        "empty-stages",
        "missing-stage",
        "missing-action",
        "provider",
        "owner",
        "version",
        "action-role",
        "empty-action-role",
        "action-region",
        "empty-action-region",
        "inputs",
        "outputs",
        "output-name",
        "duplicate-output",
        "full-clone",
        "extra-config",
        "region",
        "environment-region",
    ],
)
def test_rejects_conflicts_and_incompatible_actions(case):
    payload = architecture()
    config = payload["resources"][1]["config"]
    if case == "two-repositories":
        payload["resources"].append(
            dict(payload["resources"][0], name="other-repo", id="other")
        )
        payload["connections"].append(
            dict(payload["connections"][0], source="other-repo", source_id="other")
        )
    elif case in {"branch-conflict", "action-conflict"}:
        payload["connections"].append(
            dict(
                payload["connections"][0],
                connection_config={
                    "branch_name"
                    if case == "branch-conflict"
                    else "action_name": "other"
                },
            )
        )
    elif case in {"missing-role", "bad-role"}:
        config["role_arn"] = (
            None if case == "missing-role" else "arn:aws:iam::123456789012:policy/role"
        )
    elif case == "missing-store":
        config.pop("artifact_bucket_name")
    elif case == "empty-stages":
        config["stages_json"] = "[]"
    elif case in {"missing-stage", "missing-action"}:
        payload["connections"][0]["connection_config"] = {
            "stage_name" if case == "missing-stage" else "action_name": "missing"
        }
    elif case in {"region", "environment-region"}:
        payload["resources"][0]["provider_region"] = "eu-west-1"
        if case == "environment-region":
            payload["environments"].append(
                {"name": "prod", "variables": {"region": "us-east-1"}}
            )
    else:
        changes = {
            "provider": {"provider": "S3"},
            "owner": {"owner": "Custom"},
            "version": {"version": "2"},
            "action-role": {"role_arn": "arn:aws:iam::123456789012:role/action"},
            "empty-action-role": {"role_arn": ""},
            "action-region": {"region": "eu-west-1"},
            "empty-action-region": {"region": ""},
            "inputs": {"input_artifacts": ["input"]},
            "outputs": {"output_artifacts": []},
            "output-name": {"output_artifacts": ["invalid.artifact"]},
            "full-clone": {
                "configuration": {"OutputArtifactFormat": "CODEBUILD_CLONE_REF"}
            },
            "extra-config": {"configuration": {"Unexpected": "value"}},
        }
        if case == "duplicate-output":
            change_stages(
                payload,
                lambda stages: stages[1]["actions"][0].update(
                    output_artifacts=["source"]
                ),
            )
        else:
            change_stages(
                payload, lambda stages: stages[0]["actions"][0].update(changes[case])
            )
    with pytest.raises(
        CrossRegionConnectionError
        if case in {"region", "environment-region"}
        else InvalidConnectionConfigError
    ):
        generate(payload)


def test_unconnected_pipeline_and_other_source_actions_remain_unchanged():
    payload = architecture()
    change_stages(
        payload,
        lambda stages: stages[0]["actions"].append(
            {
                "name": "Other",
                "category": "Source",
                "provider": "S3",
                "output_artifacts": ["other"],
                "configuration": {
                    "S3Bucket": "external-source",
                    "S3ObjectKey": "source.zip",
                },
            }
        ),
    )
    tree = generate(payload)
    assert "external-source" in "\n".join(tree.values())
    payload["connections"] = []
    tree = generate(payload)
    assert not resources(tree, "aws_iam_role_policy")
    assert "var.repository_source" not in "\n".join(tree.values())
    payload["connections"] = architecture()["connections"]
    payload["resources"][0]["provider_region"] = "eu-west-1"
    payload["environments"][0]["variables"]["region"] = "us-west-2"
    generate(payload)


def native_values():
    ir = project(architecture())
    config = next(
        instance.config
        for module in ir.modules
        for instance in module.instances
        if instance.name == "target-resource"
    )
    stages = json.loads(config.stages_json)
    return {
        "var.role_arn": "arn:aws:iam::123456789012:role/pipeline/execution",
        "var.artifact_bucket_name": "artifacts",
        "var.repository_source": {
            "name": "application",
            "arn": "arn:aws:codecommit:us-east-1:123456789012:application",
            "stage_name": "Source",
            "action_name": "Source",
            "branch_name": "main",
        },
        "local.repository_stages": stages,
        "local.repository_action": stages[0]["actions"][0],
        "data.aws_partition.repository_source.partition": "aws",
        "data.aws_region.repository_source.region": "us-east-1",
        "data.aws_caller_identity.repository_source.account_id": "123456789012",
        "data.aws_iam_role.repository_source.arn": "arn:aws:iam::123456789012:role/pipeline/execution",
    }


@needs_terraform
@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "arn-account",
        "arn-region",
        "arn-name",
        "role-account",
        "role-path",
        "branch",
        "stage",
        "provider",
        "role",
        "region",
        "outputs",
        "producer",
        "clone",
        "store",
        "missing-action",
        "duplicate-action",
        "gov",
        "china",
    ],
)
def test_terraform_guards_and_exact_policy(tmp_path, case):
    values = native_values()
    repository = values["var.repository_source"]
    action = values["local.repository_action"]
    if case.startswith("arn-"):
        original, replacement = {
            "arn-account": ("123456789012", "111111111111"),
            "arn-region": ("us-east-1", "eu-west-1"),
            "arn-name": ("application", "other"),
        }[case]
        repository["arn"] = repository["arn"].replace(original, replacement)
    elif case == "role-account":
        values["var.role_arn"] = values["var.role_arn"].replace(
            "123456789012", "111111111111"
        )
    elif case == "role-path":
        values["data.aws_iam_role.repository_source.arn"] = values[
            "var.role_arn"
        ].replace("pipeline/", "other/")
    elif case == "branch":
        repository["branch_name"] = "branch.lock/main"
    elif case == "stage":
        repository["stage_name"] = "other"
    elif case == "provider":
        action["provider"] = "S3"
    elif case in {"role", "region"}:
        action["role_arn" if case == "role" else "region"] = "override"
    elif case == "outputs":
        action["output_artifacts"] = []
    elif case == "producer":
        values["local.repository_stages"][1]["actions"][0]["output_artifacts"] = [
            "source"
        ]
    elif case == "clone":
        action["configuration"]["OutputArtifactFormat"] = "CODEBUILD_CLONE_REF"
    elif case == "store":
        values["var.artifact_bucket_name"] = " "
    elif case == "missing-action":
        repository["action_name"] = "missing"
    elif case == "duplicate-action":
        values["local.repository_stages"][0]["actions"].append(deepcopy(action))
    elif case in {"gov", "china"}:
        partition, region = (
            ("aws-us-gov", "us-gov-west-1")
            if case == "gov"
            else ("aws-cn", "cn-north-1")
        )
        values["data.aws_partition.repository_source.partition"] = partition
        values["data.aws_region.repository_source.region"] = region
        repository["arn"] = (
            f"arn:{partition}:codecommit:{region}:123456789012:application"
        )
        values["var.role_arn"] = values["data.aws_iam_role.repository_source.arn"] = (
            f"arn:{partition}:iam::123456789012:role/pipeline/execution"
        )
    text = file_with(generate(architecture()), "/repository_source.tf")
    selector = re.search(r"  repository_action = (.*)", text)[1]
    values["local.repository_action"] = evaluate(tmp_path, selector, values)
    conditions = [item["condition"] for item in pipeline_source_policy_preconditions()]
    assert evaluate(tmp_path, "alltrue([" + ", ".join(conditions) + "])", values) is (
        case in {"valid", "gov", "china"}
    )
    if case == "valid":
        expression = re.search(r"  policy = (.*?)\n  lifecycle \{", text, re.S)[1]
        policy = json.loads(evaluate(tmp_path, expression, values))
        assert policy["Statement"][0]["Resource"] == repository["arn"]
        assert set(policy["Statement"][0]["Action"]) == {
            "codecommit:CancelUploadArchive",
            "codecommit:GetBranch",
            "codecommit:GetCommit",
            "codecommit:GetRepository",
            "codecommit:GetUploadArchiveStatus",
            "codecommit:UploadArchive",
        }
        pipeline = file_with(
            generate(architecture()), "/target-resource/codepipeline.tf"
        )
        configuration = re.search(r"\s+configuration = (.*)", pipeline)[1]
        selected = evaluate(
            tmp_path,
            configuration,
            {
                **values,
                "stage.value": values["local.repository_stages"][0],
                "action.value": action,
            },
        )
        assert selected == {
            "RepositoryName": "application",
            "BranchName": "main",
            "PollForSourceChanges": "false",
            "OutputArtifactFormat": "CODE_ZIP",
        }
        other = {
            "name": "Other",
            "configuration": {"S3Bucket": "external", "S3ObjectKey": "input.zip"},
        }
        assert (
            evaluate(
                tmp_path,
                configuration,
                {**values, "stage.value": {"name": "Source"}, "action.value": other},
            )
            == other["configuration"]
        )


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode",
    [
        "plain",
        "duplicates",
        "renamed",
        "regional",
        "artifacts",
        "encrypted-artifacts",
        "shared-role",
        "build-source",
    ],
)
def test_provider_validation_and_acyclic_composition(tmp_path, mode):
    payload = architecture()
    if mode == "duplicates":
        payload["connections"] *= 3
    elif mode == "renamed":
        change_stages(
            payload,
            lambda stages: (
                stages[0].update(name="Checkout"),
                stages[0]["actions"][0].update(name="Repository"),
            ),
        )
        payload["connections"][0]["connection_config"] = {
            "stage_name": "Checkout",
            "action_name": "Repository",
            "branch_name": "release/v2",
        }
    elif mode == "regional":
        payload["environments"][0]["variables"]["region"] = "us-west-2"
    elif mode in {"artifacts", "encrypted-artifacts"}:
        add_artifacts(payload, mode == "encrypted-artifacts")
    elif mode == "shared-role":
        payload["resources"].append(
            dict(payload["resources"][1], name="second-pipeline", id="second")
        )
        payload["connections"].append(
            dict(
                payload["connections"][0], target="second-pipeline", target_id="second"
            )
        )
    elif mode == "build-source":
        template = connection_architecture(
            resolve_spec(ServiceType.CODECOMMIT, ServiceType.CODEBUILD, None, {})
        )
        payload["resources"].append(
            dict(template["resources"][1], name="build", id="build")
        )
        payload["connections"].append(
            dict(template["connections"][0], target="build", target_id="build")
        )
    tree = generate(payload)
    payload["connections"] = list(reversed(payload["connections"] * 2))
    assert generate(payload) == tree
    if mode in {"artifacts", "encrypted-artifacts"}:
        pipeline = resources(tree, "aws_codepipeline")[0]
        assert set(pipeline["depends_on"]) == {
            "${aws_iam_role_policy.artifacts}",
            "${aws_iam_role_policy.repository_source}",
        }
        assert all(
            len(policy["lifecycle"][0]["precondition"]) == 9
            for policy in resources(tree, "aws_iam_role_policy")
        )
    _write_tree(tmp_path, tree)
    environment = tmp_path / "connection-check/environments/dev"
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], environment
    )
    _run_terraform(["validate", "-no-color"], environment)
    _run_terraform(["graph", "-type=plan"], environment)
