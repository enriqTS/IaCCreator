"""WAF connection coverage."""

from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


def _tree(target):
    spec = resolve_spec(ServiceType.WAF, target, "protects", {})
    assert spec is not None
    architecture = ArchitectureDescription.model_validate(connection_architecture(spec))
    return CodeGenerator().generate(IRBuilder().build(architecture))


def test_waf_association_is_owned_by_web_acl_module():
    tree = _tree(ServiceType.LOAD_BALANCER)
    association = tree[
        "connection-check/modules/security/waf/source-resource/association_target_resource.tf"
    ]
    assert 'resource "aws_wafv2_web_acl_association"' in association
    assert "resource_arn = var.target_resource_load_balancer_arn" in association
    assert "web_acl_arn = aws_wafv2_web_acl.source-resource.arn" in association


def test_cloudfront_receives_managed_web_acl_arn():
    tree = _tree(ServiceType.CLOUDFRONT)
    distribution = tree[
        "connection-check/modules/networking/cloudfront/target-resource/cloudfront.tf"
    ]
    environment = tree["connection-check/environments/dev/main.tf"]
    assert "web_acl_id = var.web_acl_id" in distribution
    assert "web_acl_id = module.source-resource.web_acl_arn" in environment
