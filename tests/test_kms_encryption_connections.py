"""KMS encryption connection coverage."""

import json

import pytest

from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


@pytest.mark.parametrize(
    "target,input_name",
    [
        (ServiceType.S3, "sse_kms_key_id"),
        (ServiceType.DYNAMODB, "server_side_encryption_kms_key_arn"),
        (ServiceType.SNS, "kms_master_key_id"),
        (ServiceType.SQS, "kms_master_key_id"),
        (ServiceType.CLOUDWATCH, "kms_key_id"),
        (ServiceType.EBS, "kms_key_id"),
        (ServiceType.EFS, "kms_key_id"),
        (ServiceType.BACKUP, "kms_key_arn"),
        (ServiceType.SECRETS_MANAGER, "kms_key_id"),
        (ServiceType.DATAZONE, "kms_key_identifier"),
        (ServiceType.CODEARTIFACT, "kms_key"),
        (ServiceType.LAMBDA, "kms_key_arn"),
    ],
)
def test_kms_key_arn_is_wired_to_native_service_input(target, input_name):
    spec = resolve_spec(ServiceType.KMS, target, "encrypts", {})
    assert spec is not None
    tree = CodeGenerator().generate(
        IRBuilder().build(
            ArchitectureDescription.model_validate(connection_architecture(spec))
        )
    )
    environment = tree["connection-check/environments/dev/main.tf"]
    assert f"{input_name} = module.source-resource.key_arn" in environment


def test_lambda_receives_scoped_kms_decrypt_grant():
    spec = resolve_spec(ServiceType.KMS, ServiceType.LAMBDA, "encrypts", {})
    tree = CodeGenerator().generate(
        IRBuilder().build(
            ArchitectureDescription.model_validate(connection_architecture(spec))
        )
    )
    policy = json.loads(
        tree["connection-check/iam-policies/target-resource-policy.json"]
    )
    statement = next(
        item for item in policy["Statement"] if "kms:Decrypt" in item["Action"]
    )
    assert statement["Resource"] == "${var.kms_key_arn}"


@pytest.mark.parametrize("duplicate", [False, True])
def test_sqs_encryption_renders_native_reference_without_duplicate_variables(duplicate):
    spec = resolve_spec(ServiceType.KMS, ServiceType.SQS, "encrypts", {})
    payload = connection_architecture(spec)
    payload["resources"][1]["config"]["kms_master_key_id"] = "alias/external"
    if duplicate:
        payload["connections"].append(dict(payload["connections"][0]))
    project = IRBuilder().build(ArchitectureDescription.model_validate(payload))

    from app.services.connection_previewer import ConnectionPreviewer

    previews = ConnectionPreviewer().preview_all(project)
    assert all(preview.issues == [] for preview in previews)
    assert all(preview.label == "KMS → sqs" for preview in previews)
    tree = CodeGenerator().generate(project)
    queue_files = {
        path.rsplit("/", 1)[-1]: text
        for path, text in tree.items()
        if "/sqs/target-resource/" in path
    }
    assert "kms_master_key_id = var.kms_master_key_id" in queue_files["sqs.tf"]
    assert queue_files["variables.tf"].count('variable "kms_master_key_id"') == 1
    environment = tree["connection-check/environments/dev/main.tf"]
    assert environment.count("kms_master_key_id = module.source-resource.key_arn") == 1

    from tests.hcl_assertions import assert_tree_parses

    assert_tree_parses(tree)


@pytest.mark.parametrize(
    "key", [None, "alias/external", "arn:aws:kms:us-east-1:123456789012:key/example"]
)
def test_sqs_preserves_external_key_configuration(key):
    from app.generators.sqs_generator import SQSGenerator
    from app.models.input_models.sqs_config import SqsConfig
    from tests.generator_helpers import make_instance

    instance = make_instance("queue", ServiceType.SQS, SqsConfig(kms_master_key_id=key))
    generator = SQSGenerator()
    resource = generator.generate_resource_tf(instance)
    variables = generator.generate_variables_tf(instance)
    assert ("kms_master_key_id = var.kms_master_key_id" in resource) == (
        key is not None
    )
    if key is not None:
        assert f'default = "{key}"' in " ".join(variables.split())


def test_sqs_encryption_rejects_reverse_direction():
    assert resolve_spec(ServiceType.SQS, ServiceType.KMS, "encrypts", {}) is None
