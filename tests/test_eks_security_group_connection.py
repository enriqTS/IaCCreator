"""EKS security-group placement coverage."""

from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


def test_security_group_connection_wires_eks_vpc_config():
    spec = resolve_spec(ServiceType.SECURITY_GROUP, ServiceType.EKS, "associates", {})
    assert spec is not None

    architecture = ArchitectureDescription.model_validate(connection_architecture(spec))
    tree = CodeGenerator().generate(IRBuilder().build(architecture))

    resource = tree["connection-check/modules/compute/eks/target-resource/eks.tf"]
    variables = tree[
        "connection-check/modules/compute/eks/target-resource/variables.tf"
    ]
    environment = tree["connection-check/environments/dev/main.tf"]

    assert "security_group_ids = var.security_group_ids" in resource
    assert 'variable "security_group_ids"' in variables
    assert (
        "security_group_ids = [module.source-resource.security_group_id]" in environment
    )
