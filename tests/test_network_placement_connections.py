from app.models.input_models import ServiceType
from app.models.input_models.lambda_config import LambdaConfig
from app.models.input_models.subnet_config import SubnetConfig
from app.models.ir_models import (
    ConnectionIR,
    ProjectIR,
    ResourceInstanceIR,
    ServiceModuleIR,
)
from app.services.connection_handlers.network_placement import (
    SubnetListPlacementHandler,
)


def test_list_placement_aggregates_sorted_unique_sources() -> None:
    connections = [
        ConnectionIR(
            source_name=name,
            target_name="function",
            source_service=ServiceType.SUBNET,
            target_service=ServiceType.LAMBDA,
            connection_type="places",
        )
        for name in ("subnet_b", "subnet_a", "subnet_a")
    ]
    instances = [
        ResourceInstanceIR(
            name=name,
            service_type=ServiceType.SUBNET,
            config=SubnetConfig(),
        )
        for name in ("subnet_a", "subnet_b")
    ]
    function = ResourceInstanceIR(
        name="function",
        service_type=ServiceType.LAMBDA,
        config=LambdaConfig(function_name="function"),
    )
    project = ProjectIR(
        project_name="placement",
        environments=[],
        modules=[
            ServiceModuleIR(service_type=ServiceType.SUBNET, instances=instances),
            ServiceModuleIR(service_type=ServiceType.LAMBDA, instances=[function]),
        ],
        connections=connections,
    )

    contribution = SubnetListPlacementHandler("vpc_subnet_ids").handle(
        connections[0], project
    )

    assert contribution.inputs[0].value == (
        "[module.subnet_a.subnet_id, module.subnet_b.subnet_id]"
    )
    assert function.config.vpc_subnet_ids == ["managed-by-connection"]
