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
