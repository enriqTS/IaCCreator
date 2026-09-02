"""ECS target-group connection coverage."""

from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


def test_ecs_service_receives_target_group_block_and_port_mapping():
    spec = resolve_spec(ServiceType.TARGET_GROUP, ServiceType.ECS, "serves", {})
    assert spec is not None
    payload = connection_architecture(spec)
    payload["connections"][0]["connection_config"] = {"container_port": 8080}
    tree = CodeGenerator().generate(
        IRBuilder().build(ArchitectureDescription.model_validate(payload))
    )
    resource = tree["connection-check/modules/compute/ecs/target-resource/ecs.tf"]
    environment = tree["connection-check/environments/dev/main.tf"]
    assert "load_balancer" in resource
    assert "target_group_arn = var.source_resource_target_group_arn" in resource
    assert "container_port = 8080" in resource
    assert (
        '\\"containerPort\\": 8080'
        in tree["connection-check/modules/compute/ecs/target-resource/variables.tf"]
    )
    assert (
        "source_resource_target_group_arn = module.source-resource.target_group_arn"
        in environment
    )
