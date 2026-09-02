"""Global Accelerator connection coverage."""

from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


def _tree(source, target, kind):
    spec = resolve_spec(source, target, kind, {})
    assert spec is not None
    return CodeGenerator().generate(
        IRBuilder().build(
            ArchitectureDescription.model_validate(connection_architecture(spec))
        )
    )


def test_accelerator_owns_listener_and_endpoint_group():
    tree = _tree(
        ServiceType.GLOBAL_ACCELERATOR, ServiceType.LOAD_BALANCER, "accelerates"
    )
    prefix = "connection-check/modules/networking/global-accelerator/source-resource"
    assert (
        'resource "aws_globalaccelerator_listener"'
        in tree[f"{prefix}/listener_target_resource.tf"]
    )
    group = tree[f"{prefix}/endpoint_group_target_resource.tf"]
    assert 'resource "aws_globalaccelerator_endpoint_group"' in group
    assert "endpoint_id = var.target_resource_load_balancer_arn" in group


def test_route53_aliases_accelerator_outputs():
    tree = _tree(ServiceType.ROUTE53, ServiceType.GLOBAL_ACCELERATOR, "aliases")
    environment = tree["connection-check/environments/dev/main.tf"]
    assert (
        "target_resource_alias_dns_name = module.target-resource.dns_name"
        in environment
    )
    assert (
        "target_resource_alias_zone_id = module.target-resource.hosted_zone_id"
        in environment
    )
