"""Route 53 alias connection coverage."""

import pytest

from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


@pytest.mark.parametrize(
    "target,dns_output,zone_output",
    [
        (ServiceType.LOAD_BALANCER, "dns_name", "zone_id"),
        (ServiceType.CLOUDFRONT, "domain_name", "hosted_zone_id"),
    ],
)
def test_route53_alias_uses_managed_target_outputs(target, dns_output, zone_output):
    spec = resolve_spec(ServiceType.ROUTE53, target, "aliases", {})
    assert spec is not None
    payload = connection_architecture(spec)
    payload["connections"][0]["connection_config"] = {
        "record_name": "app",
        "evaluate_target_health": True,
    }
    tree = CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(payload))
    )

    record = tree[
        "connection-check/modules/networking/route53/source-resource/"
        "alias_target_resource.tf"
    ]
    environment = tree["connection-check/environments/dev/main.tf"]

    assert 'resource "aws_route53_record"' in record
    assert 'name = "app"' in record
    assert "evaluate_target_health = true" in record
    assert "name = var.target_resource_alias_dns_name" in record
    assert "zone_id = var.target_resource_alias_zone_id" in record
    assert (
        f"target_resource_alias_dns_name = module.target-resource.{dns_output}"
        in environment
    )
    assert (
        f"target_resource_alias_zone_id = module.target-resource.{zone_output}"
        in environment
    )
