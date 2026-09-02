"""Target-group attachment coverage for EC2 Auto Scaling."""

from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


def test_target_group_arn_is_wired_to_auto_scaling_group():
    spec = resolve_spec(
        ServiceType.TARGET_GROUP, ServiceType.EC2_AUTO_SCALING, "attaches", {}
    )
    assert spec is not None

    architecture = ArchitectureDescription.model_validate(connection_architecture(spec))
    tree = CodeGenerator().generate(IRBuilder().build(architecture))

    resource = tree[
        "connection-check/modules/compute/ec2-auto-scaling/target-resource/ec2-auto-scaling.tf"
    ]
    environment = tree["connection-check/environments/dev/main.tf"]

    assert "target_group_arns = var.target_group_arns" in resource
    assert (
        "target_group_arns = [module.source-resource.target_group_arn]" in environment
    )
