import pytest
from pydantic import ValidationError

from app.models.containment import ContainmentOperation
from app.models.diagram_models import DiagramStateInput
from app.services.containment_operation_service import ContainmentOperationService


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
    return {
        "id": object_id,
        "objectType": "architecture-block",
        "serviceType": service,
        "name": object_id,
        "x": 0,
        "y": 0,
        "config": {},
        "terraformVariables": {},
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


def test_rejects_cycle_and_non_container_parent():
    with pytest.raises(ValidationError, match="cycle"):
        diagram([container("a", "generic", "b"), container("b", "generic", "a")])

    with pytest.raises(ValidationError, match="not container-capable"):
        diagram([resource("vpc", "vpc"), resource("subnet", "subnet", "vpc")])
