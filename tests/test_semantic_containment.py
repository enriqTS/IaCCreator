import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.models.containment import ContainmentOperation
from app.models.diagram_models import DiagramStateInput
from app.models.input_models import ServiceType
from app.services.code_generator import CodeGenerator
from app.services.containment_catalog import build_containment_catalog
from app.services.containment_operation_service import ContainmentOperationService
from app.services.containment_resolver import ContainmentResolver
from app.services.diagram_converter import DiagramConverter
from app.services.diagram_normalizer import DiagramNormalizer
from app.services.ir_builder import IRBuilder
from app.services.resource_initializer import ResourceInitializer


def diagram(objects, environments=None):
    return DiagramStateInput.model_validate(
        {
            "version": 4,
            "projectName": "scopes",
            "environments": environments or [],
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


def test_catalog_defines_typed_architecture_boundaries():
    catalog = build_containment_catalog()
    definitions = {item.container_type: item for item in catalog.container_types}

    assert definitions["organization"].allowed_child_types == [
        "account",
        "organizational-unit",
    ]
    assert "region" in definitions["account"].allowed_child_types


def test_typed_boundaries_can_nest_deployment_scopes():
    state = diagram(
        [
            container("organization", "organization"),
            container("unit", "organizational-unit", "organization"),
            container("account", "account", "unit"),
            container("region", "region", "account", {"region": "us-east-1"}),
        ]
    )

    normalized = DiagramNormalizer().normalize(state.model_dump(mode="json"))

    assert normalized.canvasObjects[-1].parentContainerId == "account"


def test_reports_typed_issue_for_unsupported_cross_region_connection():
    state = diagram(
        [
            container("east", "region", config={"region": "us-east-1"}),
            resource("east-vpc", "vpc", "east", "container"),
            resource("east-subnet", "subnet", "east-vpc", "container"),
            container("west", "region", config={"region": "us-west-2"}),
            resource("west-vpc", "vpc", "west", "container"),
            resource("west-subnet", "subnet", "west-vpc", "container"),
            resource("function", "lambda", "west-subnet"),
        ]
    )
    payload = state.model_dump(mode="json")
    payload["connectors"] = [
        {
            "id": "cross-region-placement",
            "sourceId": "east-subnet",
            "targetId": "function",
            "connectionType": "places",
        }
    ]

    resolution = ContainmentResolver().resolve(
        DiagramStateInput.model_validate(payload)
    )

    assert any(issue.code == "cross-region-connection" for issue in resolution.issues)


def test_multi_region_containment_selects_provider_aliases_for_modules():
    state = diagram(
        [
            container("east", "region", config={"region": "us-east-1"}),
            resource("east-vpc", "vpc", "east"),
            container("west", "region", config={"region": "us-west-2"}),
            resource("west-vpc", "vpc", "west"),
        ]
    )

    canonical = DiagramNormalizer().normalize(state.model_dump(mode="json"))
    architecture = DiagramConverter().convert(canonical)
    tree = CodeGenerator().generate(IRBuilder().build(architecture))

    provider = tree["scopes/environments/dev/provider.tf"]
    main = tree["scopes/environments/dev/main.tf"]
    assert 'alias = "us_west_2"' in provider
    assert 'region = "us-west-2"' in provider
    assert "providers = { aws = aws.us_west_2 }" in main


def test_resolves_environment_specific_scope_views_without_copying_resources():
    state = diagram(
        [container("region", "region", config={"region": "us-east-1"})],
        environments=[
            {"name": "development", "variables": {}},
            {"name": "recovery", "variables": {"region": "us-west-2"}},
        ],
    )

    resolution = ContainmentResolver().resolve(state)
    views = {view.environment: view for view in resolution.environment_scopes}

    assert views["development"].effective_scopes[0].region == "us-east-1"
    assert views["recovery"].effective_scopes[0].region == "us-west-2"
    assert len(state.canvasObjects) == 1


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


def test_private_zone_containment_generates_vpc_association():
    state = diagram(
        [
            resource("vpc", "vpc", presentation="container"),
            resource("zone", "route53", "vpc"),
        ]
    )

    canonical = DiagramNormalizer().normalize(state.model_dump(mode="json"))
    architecture = DiagramConverter().convert(canonical)
    tree = CodeGenerator().generate(IRBuilder().build(architecture))

    main = tree["scopes/environments/dev/main.tf"]
    assert "vpc_id = module.vpc.vpc_id" in main
    assert "private_zone = true" in main
    assert canonical.connectors[0].connectionType == "contains"


def test_rejected_operation_returns_typed_issue_and_original_state():
    state = diagram([resource("vpc", "vpc"), resource("subnet", "subnet")])

    result = ContainmentOperationService().apply(
        state,
        ContainmentOperation(operation="assign", object_id="subnet", parent_id="vpc"),
    )

    subnet = next(obj for obj in result.diagram.canvasObjects if obj.id == "subnet")
    assert subnet.parentContainerId is None
    assert result.resolution.issues[-1].code == "invalid-parent-type"


def test_rejects_az_and_managed_identity_conflicts():
    az_state = diagram(
        [
            container("region", "region", config={"region": "us-east-1"}),
            container(
                "az",
                "availability-zone",
                "region",
                {"availability_zone": "eu-west-1a"},
            ),
        ]
    )
    az_result = ContainmentOperationService().apply(
        az_state,
        ContainmentOperation(
            operation="set-scope",
            object_id="az",
            config={"availability_zone": "eu-west-1a"},
        ),
    )
    assert az_result.resolution.issues[-1].code == "availability-zone-conflict"

    identity_payload = diagram(
        [
            resource("vpc", "vpc", presentation="container"),
            resource("subnet", "subnet", "vpc"),
        ]
    ).model_dump(mode="json")
    identity_payload["canvasObjects"][1]["config"]["vpc_id"] = "vpc-external"
    identity_state = DiagramStateInput.model_validate(identity_payload)
    identity_result = ContainmentOperationService().apply(
        identity_state,
        ContainmentOperation(
            operation="set-presentation",
            object_id="vpc",
            presentation="container",
        ),
    )
    assert identity_result.resolution.issues[-1].code == "configuration-conflict"


def test_semantic_state_round_trips_without_redundant_child_collections():
    original = diagram(
        [
            container("region", "region", config={"region": "us-east-1"}),
            resource("vpc", "vpc", "region", "container"),
            resource("subnet", "subnet", "vpc"),
        ]
    )
    normalized = DiagramNormalizer().normalize(original.model_dump(mode="json"))
    restored = DiagramStateInput.model_validate(normalized.model_dump(mode="json"))

    assert restored == normalized
    assert restored.canvasObjects[2].parentContainerId == "vpc"
    assert restored.connectors[0].origin == "containment"
    assert "children" not in restored.model_dump(mode="json")["canvasObjects"][1]


@given(depth=st.integers(min_value=1, max_value=40))
def test_arbitrary_nested_trees_round_trip_deterministically(depth):
    objects = [
        container(
            f"container-{index}",
            "generic",
            f"container-{index - 1}" if index else None,
        )
        for index in range(depth)
    ]
    state = diagram(objects)

    first = DiagramNormalizer().normalize(state.model_dump(mode="json"))
    second = DiagramNormalizer().normalize(first.model_dump(mode="json"))

    assert first == second
    assert len(first.canvasObjects) == depth


@given(depth=st.integers(min_value=2, max_value=20))
def test_cycle_assignments_are_rejected_without_mutating_arbitrary_trees(depth):
    state = diagram(
        [
            container(
                f"container-{index}",
                "generic",
                f"container-{index - 1}" if index else None,
            )
            for index in range(depth)
        ]
    )

    result = ContainmentOperationService().apply(
        state,
        ContainmentOperation(
            operation="assign",
            object_id="container-0",
            parent_id=f"container-{depth - 1}",
        ),
    )

    assert result.diagram == state
    assert result.resolution.issues[-1].code == "containment-cycle"


def test_rejects_cycle_and_non_container_parent():
    with pytest.raises(ValidationError, match="cycle"):
        diagram([container("a", "generic", "b"), container("b", "generic", "a")])

    with pytest.raises(ValidationError, match="not container-capable"):
        diagram([resource("vpc", "vpc"), resource("subnet", "subnet", "vpc")])
