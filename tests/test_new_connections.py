"""The connections added on top of the wiring model."""

import json

import pytest
from fastapi import HTTPException

from app.generators.schema_validator import validate_config_against_schema
from app.models.input_models import ArchitectureDescription, ServiceType
from app.models.input_models.dynamodb_config import DynamoDBConfig
from app.models.input_models.eventbridge_config import EventBridgeConfig
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import CONNECTION_REGISTRY, resolve_spec
from app.services.ir_builder import IRBuilder
from tests.reference_project import reference_architecture, reference_tree


@pytest.fixture(scope="module")
def tree():
    return reference_tree()


class TestS3NotifiesLambda:
    def test_notification_lives_in_the_bucket_module(self, tree):
        path = "reference-project/modules/storage/s3/uploads/notification_on-upload.tf"
        assert 'resource "aws_s3_bucket_notification"' in tree[path]

    def test_function_arn_arrives_as_a_module_input(self, tree):
        path = "reference-project/modules/storage/s3/uploads/notification_on-upload.tf"
        assert "var.on_upload_function_arn" in tree[path]

    def test_configured_filters_are_emitted(self, tree):
        path = "reference-project/modules/storage/s3/uploads/notification_on-upload.tf"
        assert 'filter_suffix = ".csv"' in tree[path]

    def test_permission_precedes_the_notification(self, tree):
        path = "reference-project/modules/storage/s3/uploads/notification_on-upload.tf"
        assert "depends_on" in tree[path]

    def test_environment_wires_the_function_arn(self, tree):
        main = tree["reference-project/environments/dev/main.tf"]
        assert "on_upload_function_arn = module.on-upload.function_arn" in main

    def test_config_driven_notification_defers_to_the_connection(self):
        architecture = reference_architecture()
        for resource in architecture.resources:
            if resource.name == "uploads":
                resource.config.notification_lambda_arn = "arn:aws:lambda:::function:x"
        generated = CodeGenerator().generate(IRBuilder().build(architecture))
        # AWS permits exactly one notification resource per bucket
        blocks = sum(
            content.count('resource "aws_s3_bucket_notification"')
            for path, content in generated.items()
            if "uploads" in path
        )
        assert blocks == 1


class TestDynamoDBStreamsToLambda:
    def test_mapping_lives_in_the_function_module(self, tree):
        path = "reference-project/modules/compute/lambda/on-change/stream_users.tf"
        assert 'resource "aws_lambda_event_source_mapping"' in tree[path]

    def test_stream_arn_arrives_as_a_module_input(self, tree):
        path = "reference-project/modules/compute/lambda/on-change/stream_users.tf"
        assert "var.users_stream_arn" in tree[path]

    def test_configured_batch_size_is_used(self, tree):
        path = "reference-project/modules/compute/lambda/on-change/stream_users.tf"
        assert "batch_size = 50" in tree[path]

    def test_table_exposes_its_stream_arn(self, tree):
        outputs = tree["reference-project/modules/database/dynamodb/users/outputs.tf"]
        assert 'output "stream_arn"' in outputs

    def test_function_is_granted_stream_actions(self, tree):
        policy = json.loads(
            tree["reference-project/iam-policies/on-change-policy.json"]
        )
        actions = [a for s in policy["Statement"] for a in s["Action"]]
        assert "dynamodb:GetRecords" in actions
        assert "dynamodb:DescribeStream" in actions


class TestEcsIsARoleOwner:
    def test_task_role_is_generated(self, tree):
        iam = tree["reference-project/modules/compute/ecs/worker/iam.tf"]
        assert "ecs-tasks.amazonaws.com" in iam

    def test_connection_grants_reach_the_task_role(self, tree):
        policy = json.loads(tree["reference-project/iam-policies/worker-policy.json"])
        actions = [a for s in policy["Statement"] for a in s["Action"]]
        assert "dynamodb:GetItem" in actions
        assert "s3:PutObject" in actions

    def test_base_statements_are_the_services_own(self, tree):
        policy = json.loads(tree["reference-project/iam-policies/worker-policy.json"])
        actions = [a for s in policy["Statement"] for a in s["Action"]]
        assert "ecr:GetAuthorizationToken" in actions
        assert not any(a.startswith("logs:CreateLogGroup") for a in actions)


class TestRegistryGrowth:
    @pytest.mark.parametrize(
        "source,target,connection_type",
        [
            (ServiceType.S3, ServiceType.LAMBDA, "notifies"),
            (ServiceType.DYNAMODB, ServiceType.LAMBDA, "streams_to"),
            (ServiceType.ECS, ServiceType.DYNAMODB, "accesses"),
            (ServiceType.ECS, ServiceType.S3, "accesses"),
        ],
    )
    def test_new_pairs_are_registered(self, source, target, connection_type):
        assert (source, target, connection_type) in CONNECTION_REGISTRY

    def test_shared_grant_handler_serves_several_pairs(self):
        lambda_spec = resolve_spec(ServiceType.LAMBDA, ServiceType.S3, "accesses", {})
        ecs_spec = resolve_spec(ServiceType.ECS, ServiceType.S3, "accesses", {})
        assert type(lambda_spec.handler) is type(ecs_spec.handler)


class TestStreamsAreEnabledByTheConnection:
    """A table that never opted into streams still has to have one to be consumed."""

    @staticmethod
    def _tree(table_config: dict, connection_config: dict) -> dict:
        arch = ArchitectureDescription.model_validate(
            {
                "project_name": "p",
                "environments": [{"name": "dev", "variables": {}}],
                "resources": [
                    {
                        "id": "t1",
                        "name": "orders",
                        "service_type": "dynamodb",
                        "config": {
                            "table_name": "orders",
                            "hash_key": "id",
                            "hash_key_type": "S",
                            **table_config,
                        },
                        "terraform_variables": {},
                    },
                    {
                        "id": "f1",
                        "name": "consumer",
                        "service_type": "lambda",
                        "config": {"function_name": "consumer"},
                        "terraform_variables": {},
                    },
                ],
                "connections": [
                    {
                        "source": "orders",
                        "target": "consumer",
                        "source_id": "t1",
                        "target_id": "f1",
                        "connection_type": "streams_to",
                        "connection_config": connection_config,
                    }
                ],
                "global_terraform_config": {
                    "backend_type": "local",
                    "backend_config": {},
                    "provider_region": "us-east-1",
                },
            }
        )
        return CodeGenerator().generate(IRBuilder().build(arch))

    @staticmethod
    def _variable_default(tree: dict, name: str) -> str:
        body = tree["p/modules/database/dynamodb/orders/variables.tf"]
        block = body.split(f'variable "{name}"')[1].split("}")[0]
        return next(line for line in block.splitlines() if "default" in line).strip()

    def test_table_that_never_opted_in_still_gets_a_stream(self):
        tree = self._tree({}, {})
        assert (
            "stream_enabled = var.stream_enabled"
            in (tree["p/modules/database/dynamodb/orders/dynamodb.tf"])
        )
        assert "true" in self._variable_default(tree, "stream_enabled")

    def test_connection_supplies_the_view_type(self):
        tree = self._tree({}, {"stream_view_type": "KEYS_ONLY"})
        assert "KEYS_ONLY" in self._variable_default(tree, "stream_view_type")

    def test_the_tables_own_view_type_wins(self):
        tree = self._tree(
            {"stream_enabled": True, "stream_view_type": "NEW_IMAGE"},
            {"stream_view_type": "KEYS_ONLY"},
        )
        assert "NEW_IMAGE" in self._variable_default(tree, "stream_view_type")


class TestEventBridgeRuleNeedsATrigger:
    """A rule with neither a pattern nor a schedule is rejected by terraform and AWS."""

    @staticmethod
    def _validate(**config) -> None:
        validate_config_against_schema(
            ServiceType.EVENTBRIDGE, EventBridgeConfig(rule_name="r", **config)
        )

    def test_a_rule_without_a_trigger_is_refused(self):
        with pytest.raises(HTTPException) as exc:
            self._validate()
        assert exc.value.status_code == 422
        assert "event_pattern or schedule_expression" in exc.value.detail

    def test_an_event_pattern_is_enough(self):
        self._validate(event_pattern='{"source": ["aws.s3"]}')

    def test_a_schedule_is_enough(self):
        self._validate(schedule_expression="rate(5 minutes)")

    def test_a_malformed_schedule_is_refused(self):
        with pytest.raises(HTTPException) as exc:
            self._validate(schedule_expression="every 5 minutes")
        assert exc.value.status_code == 422


class TestClosedOptionSetsAreEnforced:
    """A field whose options are the complete set must reject anything outside it."""

    @pytest.mark.parametrize(
        ("field", "bad_value", "extra"),
        [
            ("hash_key_type", "probe", {}),
            ("range_key_type", "X", {}),
            # stream_view_type is only validated while the stream is on
            ("stream_view_type", "EVERYTHING", {"stream_enabled": True}),
        ],
    )
    def test_value_outside_the_option_set_is_refused(self, field, bad_value, extra):
        kwargs = {"table_name": "t", "hash_key": "id", "hash_key_type": "S"}
        kwargs.update(extra)
        kwargs[field] = bad_value
        with pytest.raises(HTTPException) as exc:
            validate_config_against_schema(
                ServiceType.DYNAMODB, DynamoDBConfig(**kwargs)
            )
        assert exc.value.status_code == 422
