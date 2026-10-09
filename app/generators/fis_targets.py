"""Each fault target family implements the same template attribute renderer."""

from collections.abc import Callable

from app.generators.fis_ec2 import add_ec2_fault_attributes
from app.generators.fis_ecs import add_ecs_fault_attributes
from app.generators.fis_eks import add_eks_fault_attributes
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models import ServiceType

FIS_TARGET_RENDERERS: dict[ServiceType, Callable[[dict, HCLRenderer], None]] = {
    ServiceType.EC2: add_ec2_fault_attributes,
    ServiceType.ECS: add_ecs_fault_attributes,
    ServiceType.EKS: add_eks_fault_attributes,
}
