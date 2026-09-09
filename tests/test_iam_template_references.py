"""IAM policy files must evaluate resource references rather than send placeholders."""

import json
import shutil
import subprocess

import pytest

from app.generators.hcl_renderer import HCLRenderer
from app.generators.iam_policy_generator import IAMPolicyGenerator
from app.generators.iam_references import cross_module_inputs, template_context
from app.models.input_models import LambdaConfig, ServiceType
from app.models.ir_models import IAMStatement, ResourceInstanceIR


def test_policy_template_evaluates_key_arn(tmp_path):
    if shutil.which("terraform") is None:
        pytest.skip("terraform binary not installed")
    instance = ResourceInstanceIR(
        name="worker",
        service_type=ServiceType.LAMBDA,
        config=LambdaConfig(function_name="worker"),
        iam_statements=[
            IAMStatement(actions=["kms:Decrypt"], resources=["${var.kms_key_arn}"])
        ],
    )
    (tmp_path / "policy.json").write_text(
        IAMPolicyGenerator().generate_policy_document(instance)
    )
    (tmp_path / "main.tf").write_text(
        'variable "kms_key_arn" { default = "arn:aws:kms:us-east-1:123456789012:key/example" }'
    )
    context = HCLRenderer().render_expression(template_context(instance))
    (tmp_path / "context.tf").write_text(f"locals {{ policy_context = {context} }}")
    result = subprocess.run(
        ["terraform", "console"],
        cwd=tmp_path,
        input='jsonencode(jsondecode(templatefile("policy.json", local.policy_context)))\n',
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    policy = json.loads(json.loads(result.stdout))
    assert (
        policy["Statement"][-1]["Resource"]
        == "arn:aws:kms:us-east-1:123456789012:key/example"
    )


def test_foreign_resource_references_become_module_inputs():
    instance = ResourceInstanceIR(
        name="worker",
        service_type=ServiceType.LAMBDA,
        config=LambdaConfig(function_name="worker"),
        iam_statements=[
            IAMStatement(
                actions=["s3:GetObject"], resources=["${aws_s3_bucket.storage.arn}/*"]
            )
        ],
    )
    contribution = cross_module_inputs(instance)
    assert contribution.outputs[0].module == "storage"
    assert contribution.outputs[0].value == "aws_s3_bucket.storage.arn"
    assert contribution.inputs[0].module == "worker"
    assert (
        template_context(instance)["aws_s3_bucket"]["storage"]["arn"]
        == "var." + contribution.inputs[0].name
    )
