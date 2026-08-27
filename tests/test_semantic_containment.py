import pytest
from pydantic import ValidationError

from app.models.containment import ContainmentOperation
from app.models.diagram_models import DiagramStateInput
from app.models.input_models import ServiceType
from app.services.code_generator import CodeGenerator
from app.services.containment_operation_service import ContainmentOperationService
from app.services.diagram_converter import DiagramConverter
from app.services.diagram_normalizer import DiagramNormalizer
from app.services.ir_builder import IRBuilder
from app.services.resource_initializer import ResourceInitializer


def diagram(objects):
    return DiagramStateInput.model_validate(
        {
            "version": 4,
            "projectName": "scopes",
            "environments": [],
            "canvasObjects": objects,
            "connectors": [],
            "viewport": {},
        }
    )


def container(object_id, kind, parent=None, config=None):
    return {
        "id": object_id,
        "objectType": "semantic-container",
        "containerType": kind,
        "name": object_id,
        "x": 0,
        "y": 0,
        "config": config or {},
        "visualConfig": {},
        "parentContainerId": parent,
    }


def resource(object_id, service, parent=None, presentation="node"):
    service_type = ServiceType(service)
    return {
        "id": object_id,
        "objectType": "architecture-block",
        "serviceType": service,
        "name": object_id,
        "x": 0,
        "y": 0,
        "config": ResourceInitializer.config_defaults(service_type),
        "terraformVariables": ResourceInitializer.terraform_defaults(service_type),
        "visualConfig": {},
        "parentContainerId": parent,
        "presentation": presentation,
    }


def test_resolves_nested_availability_zone_for_subnet():
    state = diagram(
        [
            container("region", "region", config={"region": "us-east-1"}),
            container(
                "az", "availability-zone", "region", {"availability_zone": "us-east-1a"}
            ),
            resource("vpc", "vpc", "az", "container"),
            resource("subnet", "subnet", "vpc"),
        ]
    )

    result = ContainmentOperationService().apply(
        state,
        ContainmentOperation(
            operation="set-presentation", object_id="subnet", presentation="container"
        ),
    )

    scope = next(
        item
        for item in result.resolution.effective_scopes
        if item.object_id == "subnet"
    )
    assert scope.region == "us-east-1"
    assert scope.availability_zone == "us-east-1a"
    assert scope.vpc_id == "vpc"
    assert result.resolution.inherited_values[0].field == "availability_zone"
    assert result.diagram.canvasObjects[3].config["availability_zone"] == "us-east-1a"
    assert len(result.diagram.connectors) == 1
    assert result.diagram.connectors[0].origin == "containment"
    assert result.diagram.connectors[0].sourceId == "vpc"


def test_security_group_resolves_vpc_through_subnet_and_deduplicates_explicit():
    state = diagram(
        [
            resource("vpc", "vpc", presentation="container"),
            resource("subnet", "subnet", "vpc", "container"),
            resource("security", "security-group", "subnet"),
        ]
    )
    payload = state.model_dump(mode="json")
    payload["connectors"] = [
        {
            "id": "explicit-membership",
            "sourceId": "vpc",
            "targetId": "security",
            "connectionType": "contains",
        }
    ]
    state = DiagramStateInput.model_validate(payload)

    result = ContainmentOperationService().apply(
        state,
        ContainmentOperation(
            operation="set-presentation",
            object_id="subnet",
            presentation="container",
        ),
    )

    security_scope = next(
        item
        for item in result.resolution.effective_scopes
        if item.object_id == "security"
    )
    assert security_scope.vpc_id == "vpc"
    assert [connector.id for connector in result.diagram.connectors].count(
        "explicit-membership"
    ) == 1
    assert (
        len(
            [
                connector
                for connector in result.diagram.connectors
                if connector.targetId == "security"
            ]
        )
        == 1
    )


def test_containment_connection_generates_vpc_module_reference():
    state = diagram(
        [
            resource("vpc", "vpc", presentation="container"),
            resource("subnet", "subnet", "vpc"),
        ]
    )
    canonical = DiagramNormalizer().normalize(state.model_dump(mode="json"))
    architecture = DiagramConverter().convert(canonical)
    tree = CodeGenerator().generate(IRBuilder().build(architecture))

    main = tree["scopes/environments/dev/main.tf"]
    assert "vpc_id = module.vpc.vpc_id" in main
    assert canonical.connectors[0].origin == "containment"


def test_rejects_cycle_and_non_container_parent():
    with pytest.raises(ValidationError, match="cycle"):
        diagram([container("a", "generic", "b"), container("b", "generic", "a")])

    with pytest.raises(ValidationError, match="not container-capable"):
        diagram([resource("vpc", "vpc"), resource("subnet", "subnet", "vpc")])
