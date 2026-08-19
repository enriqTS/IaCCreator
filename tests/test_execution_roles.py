"""Execution roles are owned by any service that declares one, not just Lambda."""

import json

import pytest

from app.exceptions import GeneratorConfigError
from app.generators.execution_role_generator import ExecutionRoleGenerator
from app.generators.iam_policy_generator import IAMPolicyGenerator
from app.models.input_models import ServiceType
from app.models.input_models._base import BaseServiceConfig
from app.models.input_models.lambda_config import LambdaConfig
from app.models.input_models.s3_config import S3Config
from app.models.ir_models import IAMStatement, ResourceInstanceIR
from app.services.iam_registry import get_actions


class TaskConfig(BaseServiceConfig):
    """Stand-in for a non-Lambda service that assumes a role."""

    owns_execution_role = True
    execution_role_principal = "ecs-tasks.amazonaws.com"

    @classmethod
    def execution_role_base_statements(cls, instance_name: str) -> list[dict]:
        return [
            {
                "Effect": "Allow",
                "Action": ["ecr:GetAuthorizationToken"],
                "Resource": "*",
            }
        ]


def _instance(name: str, service_type: ServiceType, config) -> ResourceInstanceIR:
    return ResourceInstanceIR(name=name, service_type=service_type, config=config)


class TestRoleOwnership:
    def test_lambda_owns_a_role(self):
        assert LambdaConfig.owns_execution_role is True
        assert LambdaConfig.execution_role_principal == "lambda.amazonaws.com"

    def test_plain_services_do_not(self):
        assert S3Config.owns_execution_role is False
        assert BaseServiceConfig.owns_execution_role is False


class TestExecutionRoleGenerator:
    def test_uses_the_declared_principal(self):
        instance = _instance("worker", ServiceType.ECS, TaskConfig())
        hcl = ExecutionRoleGenerator().generate_iam_tf(instance)
        assert "ecs-tasks.amazonaws.com" in hcl
        assert "lambda.amazonaws.com" not in hcl

    def test_emits_role_and_policy(self):
        instance = _instance("worker", ServiceType.ECS, TaskConfig())
        hcl = ExecutionRoleGenerator().generate_iam_tf(instance)
        assert 'resource "aws_iam_role" "worker_role"' in hcl
        assert 'resource "aws_iam_role_policy" "worker_policy"' in hcl

    def test_returns_nothing_without_a_principal(self):
        instance = _instance("bucket", ServiceType.S3, S3Config())
        assert ExecutionRoleGenerator().generate_iam_tf(instance) == ""


class TestPolicyDocument:
    def test_non_lambda_owner_gets_its_own_base_statements(self):
        instance = _instance("worker", ServiceType.ECS, TaskConfig())
        document = json.loads(IAMPolicyGenerator().generate_policy_document(instance))
        actions = [a for s in document["Statement"] for a in s["Action"]]
        assert "ecr:GetAuthorizationToken" in actions
        # It must not inherit the Lambda log-group statement
        assert not any("logs:" in a for a in actions)

    def test_connection_grants_reach_a_non_lambda_owner(self):
        instance = _instance("worker", ServiceType.ECS, TaskConfig())
        instance.iam_statements.append(
            IAMStatement(actions=["s3:GetObject"], resources=["arn:aws:s3:::bucket/*"])
        )
        document = json.loads(IAMPolicyGenerator().generate_policy_document(instance))
        actions = [a for s in document["Statement"] for a in s["Action"]]
        assert "s3:GetObject" in actions

    def test_lambda_keeps_its_log_group_statement(self):
        config = LambdaConfig(function_name="f", handler="h", runtime="python3.12")
        instance = _instance("my-func", ServiceType.LAMBDA, config)
        document = json.loads(IAMPolicyGenerator().generate_policy_document(instance))
        resources = [s["Resource"] for s in document["Statement"]]
        assert "arn:aws:logs:*:*:log-group:/aws/lambda/my-func:*" in resources


class TestIamRegistryFailsLoudly:
    def test_unregistered_service_raises(self):
        with pytest.raises(GeneratorConfigError, match="No IAM actions registered"):
            get_actions(ServiceType.EC2, "full")

    def test_registered_service_returns_actions(self):
        assert "s3:GetObject" in get_actions(ServiceType.S3, "read")


class TestAssemblerEmitsRolesForAnyOwner:
    """The file tree must place role files by ownership, not by service type."""

    def test_non_lambda_owner_gets_iam_files(self, monkeypatch):
        from app.models.input_models import (
            ArchitectureDescription,
            EnvironmentConfig,
            ResourceInstance,
        )
        from app.models.input_models.ecs_config import EcsConfig
        from app.services.code_generator import CodeGenerator
        from app.services.ir_builder import IRBuilder

        monkeypatch.setattr(EcsConfig, "owns_execution_role", True, raising=False)
        monkeypatch.setattr(
            EcsConfig,
            "execution_role_principal",
            "ecs-tasks.amazonaws.com",
            raising=False,
        )

        arch = ArchitectureDescription(
            project_name="proj",
            environments=[EnvironmentConfig(name="dev")],
            resources=[
                ResourceInstance(
                    name="worker",
                    service_type=ServiceType.ECS,
                    config=EcsConfig(cluster_name="worker"),
                )
            ],
            connections=[],
        )
        tree = CodeGenerator().generate(IRBuilder().build(arch))

        iam_tf = next(p for p in tree if p.endswith("/worker/iam.tf"))
        assert "ecs-tasks.amazonaws.com" in tree[iam_tf]
        assert "proj/iam-policies/worker-policy.json" in tree

    def test_plain_service_gets_no_iam_files(self):
        from app.models.input_models import (
            ArchitectureDescription,
            EnvironmentConfig,
            ResourceInstance,
        )
        from app.services.code_generator import CodeGenerator
        from app.services.ir_builder import IRBuilder

        arch = ArchitectureDescription(
            project_name="proj",
            environments=[EnvironmentConfig(name="dev")],
            resources=[
                ResourceInstance(
                    name="bucket",
                    service_type=ServiceType.S3,
                    config=S3Config(bucket_name="bucket"),
                )
            ],
            connections=[],
        )
        tree = CodeGenerator().generate(IRBuilder().build(arch))

        assert not any(p.endswith("/iam.tf") for p in tree)
        assert not any("/iam-policies/" in p for p in tree)
