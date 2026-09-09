"""KMS data-plane permissions and service policies across supported connections."""

import json
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import CONNECTION_SPECS, resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture, minimal_config_for
from tests.hcl_assertions import assert_tree_parses


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(payload))


def add_key(payload, target_index=1, key_name="encryption-key"):
    target = payload["resources"][target_index]
    payload["resources"].append(
        {
            "id": key_name,
            "name": key_name,
            "service_type": "kms",
            "config": {"service_type": "kms"},
        }
    )
    payload["connections"].append(
        {
            "source": key_name,
            "source_id": key_name,
            "target": target["name"],
            "target_id": target["id"],
            "connection_type": "encrypts",
            "connection_config": {},
        }
    )


@pytest.mark.parametrize(
    "service,pattern,expected",
    [
        (ServiceType.S3, "read", {"kms:Decrypt"}),
        (ServiceType.S3, "write", {"kms:Decrypt", "kms:GenerateDataKey"}),
        (ServiceType.S3, "full", {"kms:Decrypt", "kms:GenerateDataKey"}),
        (ServiceType.SNS, None, {"kms:Decrypt", "kms:GenerateDataKey*"}),
        (ServiceType.SQS, None, {"kms:Decrypt", "kms:GenerateDataKey"}),
        (
            ServiceType.CLOUDWATCH,
            None,
            {
                "kms:Decrypt",
                "kms:Encrypt",
                "kms:ReEncrypt*",
                "kms:GenerateDataKey*",
                "kms:DescribeKey",
            },
        ),
    ],
)
@pytest.mark.parametrize("managed", [True, False])
def test_workload_permissions_match_actual_data_actions(
    service, pattern, expected, managed
):
    spec = resolve_spec(ServiceType.LAMBDA, service, None, {})
    payload = connection_architecture(spec)
    if pattern:
        payload["connections"][0]["connection_config"] = {"access_pattern": pattern}
    if managed:
        add_key(payload)
    else:
        field = {
            ServiceType.S3: "sse_kms_key_id",
            ServiceType.SNS: "kms_master_key_id",
            ServiceType.SQS: "kms_master_key_id",
            ServiceType.CLOUDWATCH: "kms_key_id",
        }[service]
        payload["resources"][1]["config"][field] = "alias/external-key"
        if service == ServiceType.S3:
            payload["resources"][1]["config"]["sse_algorithm"] = "aws:kms"
    ir = project(payload)
    preview = ConnectionPreviewer().preview_all(ir)[0]
    grant = next(item for item in preview.iam if "kms:Decrypt" in item.actions)
    assert set(grant.actions) == expected
    assert grant.role_owner == "source-resource"
    assert all(resource != "*" for resource in grant.resources)
    tree = CodeGenerator().generate(ir)
    assert_tree_parses(tree)
    iam = next(
        content
        for path, content in tree.items()
        if path.endswith("/source-resource/iam.tf")
    )
    assert "templatefile(" in iam
    policy = json.loads(
        tree["connection-check/iam-policies/source-resource-policy.json"]
    )
    grants = [
        statement
        for statement in policy["Statement"]
        if "kms:Decrypt" in statement["Action"]
    ]
    assert len(grants) == 1
    if managed:
        assert grants[0]["Resource"] == "${var.kms_access_target-resource_arn}"
    else:
        assert (
            grants[0]["Resource"]
            == "${data.aws_kms_key.kms_access_target-resource_arn.arn}"
        )
        assert "data.aws_kms_key.kms_access_target-resource_arn.arn" in iam


@pytest.mark.parametrize("managed", [True, False])
def test_sqs_lambda_consumer_gets_decrypt_only(managed):
    payload = connection_architecture(
        resolve_spec(ServiceType.SQS, ServiceType.LAMBDA, None, {})
    )
    if managed:
        add_key(payload, 0)
    else:
        payload["resources"][0]["config"]["kms_master_key_id"] = "alias/external-key"
    ir = project(payload)
    result = ConnectionProcessor().process_all(ir)
    grant = next(item for item in result.iam if "kms:Decrypt" in item.statement.actions)
    assert grant.role_owner == "target-resource"
    assert grant.statement.actions == ["kms:Decrypt"]
    tree = CodeGenerator().generate(ir)
    mapping = next(
        content for path, content in tree.items() if "/event_source_" in path
    )
    assert "aws_iam_role_policy.target-resource_policy" in mapping


@pytest.mark.parametrize("service", [ServiceType.S3, ServiceType.DYNAMODB])
def test_ecs_data_access_uses_service_specific_key_requirements(service):
    payload = connection_architecture(resolve_spec(ServiceType.ECS, service, None, {}))
    add_key(payload)
    result = ConnectionProcessor().process_all(project(payload))
    grants = [item for item in result.iam if "kms:Decrypt" in item.statement.actions]
    assert bool(grants) == (service == ServiceType.S3)
    tree = CodeGenerator().generate(project(payload))
    task = next(content for path, content in tree.items() if path.endswith("/ecs.tf"))
    assert "task_role_arn = aws_iam_role.source-resource_role.arn" in task
    assert "depends_on = [aws_iam_role_policy.source-resource_policy]" in task


@pytest.mark.parametrize("publisher", [ServiceType.SNS, ServiceType.EVENTBRIDGE])
def test_external_delivery_key_policy_requirements_are_reported(publisher):
    payload = connection_architecture(
        resolve_spec(publisher, ServiceType.SQS, None, {})
    )
    payload["resources"][1]["config"]["kms_master_key_id"] = "alias/external-key"
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert len(preview.issues) == 1
    assert preview.issues[0].severity == "warning"
    assert "external KMS key owner" in preview.issues[0].message
    assert not any(
        path.endswith("/key_policy.tf")
        for path in CodeGenerator().generate(project(payload))
    )


@pytest.mark.parametrize("publisher", [ServiceType.SNS, ServiceType.EVENTBRIDGE])
@pytest.mark.parametrize(
    "key", ["alias/aws/sqs", "arn:aws:kms:us-east-1:123456789012:alias/aws/sqs"]
)
def test_service_delivery_rejects_known_aws_managed_keys(publisher, key):
    payload = connection_architecture(
        resolve_spec(publisher, ServiceType.SQS, None, {})
    )
    payload["resources"][1]["config"]["kms_master_key_id"] = key
    with pytest.raises(InvalidConnectionConfigError, match="customer-managed"):
        CodeGenerator().generate(project(payload))
    add_key(payload)
    CodeGenerator().generate(project(payload))


@pytest.mark.parametrize("service", [ServiceType.EBS, ServiceType.EFS])
def test_managed_key_enables_encryption_even_when_explicitly_disabled(service):
    payload = connection_architecture(
        resolve_spec(ServiceType.KMS, service, "encrypts", {})
    )
    payload["resources"][1]["config"]["encrypted"] = False
    tree = CodeGenerator().generate(project(payload))
    assert "encrypted = true" in tree["connection-check/environments/dev/main.tf"]


def test_managed_s3_key_does_not_downgrade_dual_layer_encryption():
    payload = connection_architecture(
        resolve_spec(ServiceType.KMS, ServiceType.S3, "encrypts", {})
    )
    payload["resources"][1]["config"]["sse_algorithm"] = "aws:kms:dsse"
    tree = CodeGenerator().generate(project(payload))
    resource = next(
        content for path, content in tree.items() if path.endswith("/s3.tf")
    )
    assert "kms_master_key_id = var.sse_kms_key_id" in resource
    assert any(
        '"aws:kms:dsse"' in content
        for path, content in tree.items()
        if path.endswith("/variables.tf")
    )


def test_sns_subscriber_does_not_get_topic_decrypt_permissions():
    payload = connection_architecture(
        resolve_spec(ServiceType.SNS, ServiceType.LAMBDA, None, {})
    )
    add_key(payload, 0)
    contribution = ConnectionProcessor().process_all(project(payload))
    assert not any(
        action.startswith("kms:")
        for grant in contribution.iam
        for action in grant.statement.actions
    )


def mixed_architecture():
    payload = connection_architecture(
        resolve_spec(ServiceType.KMS, ServiceType.CLOUDTRAIL, "encrypts", {})
    )
    nodes = {
        "encryption-key": (ServiceType.KMS, {}),
        "trail": (
            ServiceType.CLOUDTRAIL,
            {"trail_name": "audit", "s3_bucket_name": "external-audit-bucket"},
        ),
        "logs": (ServiceType.CLOUDWATCH, {"log_group_name": "/app/encrypted"}),
        "topic": (ServiceType.SNS, {"topic_name": "messages"}),
        "queue": (ServiceType.SQS, {"queue_name": "messages"}),
        "rule": (
            ServiceType.EVENTBRIDGE,
            {"rule_name": "events", "event_pattern": '{"source":["example"]}'},
        ),
        "worker": (
            ServiceType.LAMBDA,
            {
                "function_name": "worker",
                "runtime": "python3.12",
                "handler": "main.handler",
                "filename": "function.zip",
            },
        ),
    }
    payload["resources"] = [
        {
            "id": name,
            "name": name,
            "service_type": service.value,
            "config": minimal_config_for(service).model_dump(exclude_none=True)
            | config,
        }
        for name, (service, config) in nodes.items()
    ]
    edges = [
        ("encryption-key", target, "encrypts")
        for target in ("trail", "logs", "topic", "queue", "worker")
    ]
    edges += [
        ("topic", "queue", "subscribes"),
        ("rule", "queue", "targets"),
        ("queue", "worker", "triggers"),
        ("worker", "logs", "logs_to"),
    ]
    payload["connections"] = [
        {
            "source": source,
            "source_id": source,
            "target": target,
            "target_id": target,
            "connection_type": kind,
            "connection_config": {},
        }
        for source, target, kind in edges
    ]
    return payload


@settings(deadline=None)
@given(reverse=st.booleans(), duplicate=st.booleans())
def test_mixed_key_policy_is_single_scoped_and_order_independent(reverse, duplicate):
    payload = mixed_architecture()
    baseline = CodeGenerator().generate(project(payload))
    if duplicate:
        payload["connections"] += deepcopy(payload["connections"])
    if reverse:
        payload["connections"].reverse()
    ir = project(payload)
    result = ConnectionProcessor().process_all(ir)
    policies = [
        resource
        for resource in result.resources
        if 'resource "aws_kms_key_policy"' in resource.content
    ]
    assert len(policies) == 1
    assert policies[0].module == "encryption-key"
    queue_policies = [
        resource
        for resource in result.resources
        if 'resource "aws_sqs_queue_policy"' in resource.content
    ]
    assert len(queue_policies) == 1
    assert queue_policies[0].module == "queue"
    assert "var.delivery_sns_arns" in queue_policies[0].content
    assert "var.delivery_eventbridge_arns" in queue_policies[0].content
    policy = policies[0].content
    for sid in (
        "EnableAccountPermissions",
        "CloudTrailEncryption",
        "CloudWatchLogsEncryption",
        "SnsQueueDelivery",
        "EventBridgeQueueDelivery",
    ):
        assert sid in policy
    assert '"kms:EncryptionContext:aws:logs:arn" = var.log_group_arns' in policy
    assert '"aws:SourceArn" = var.sqs_publisher_topic_arns' in policy
    assert "logs.${data.aws_region.kms_policy.region}" in policy
    paths = [(resource.module, resource.filename) for resource in result.resources]
    assert len(paths) == len(set(paths))
    tree = CodeGenerator().generate(ir)
    assert dict(tree) == dict(baseline)
    assert_tree_parses(tree)
    main = tree["connection-check/environments/dev/main.tf"]
    assert "module.encryption-key.service_key_arn" in main
    assert "logging_log_group = module.logs.log_group_name" in main
    assert not any(path.endswith("/log_group.tf") for path in tree)


@pytest.mark.parametrize(
    "spec",
    [spec for spec in CONNECTION_SPECS if spec.source == ServiceType.KMS],
    ids=lambda spec: spec.target.value,
)
def test_two_managed_keys_are_rejected_for_every_native_target(spec):
    payload = connection_architecture(spec)
    add_key(payload)
    with pytest.raises(InvalidConnectionConfigError, match="only one KMS key"):
        CodeGenerator().generate(project(payload))


@pytest.mark.parametrize("scenario", ["mixed", "external", "s3"])
def test_kms_projects_validate_and_have_acyclic_graphs(tmp_path, scenario):
    from tests.test_generated_project_validates import (
        _init_args,
        _run_terraform,
        _write_tree,
        needs_terraform,
    )

    if needs_terraform.args[0]:
        pytest.skip("terraform binary not installed")
    if scenario == "mixed":
        payload = mixed_architecture()
    elif scenario == "external":
        payload = connection_architecture(
            resolve_spec(ServiceType.SQS, ServiceType.LAMBDA, None, {})
        )
        payload["resources"][0]["config"]["kms_master_key_id"] = "alias/external-key"
    else:
        payload = connection_architecture(
            resolve_spec(ServiceType.LAMBDA, ServiceType.S3, None, {})
        )
        add_key(payload)
    tree = CodeGenerator().generate(project(payload))
    _write_tree(tmp_path, tree)
    environment = tmp_path / "connection-check/environments/dev"
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], environment
    )
    _run_terraform(["validate", "-no-color"], environment)
    _run_terraform(["graph", "-type=plan"], environment)
