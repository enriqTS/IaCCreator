"""Managed S3 locations preserve service ownership and external escape hatches."""

from copy import deepcopy

import pytest

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


@pytest.fixture(params=[ServiceType.ATHENA, ServiceType.LAKE_FORMATION])
def payload(request):
    return connection_architecture(resolve_spec(request.param, ServiceType.S3, "", {}))


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(deepcopy(payload)))


def test_bucket_references_and_prefixes(payload):
    payload["connections"][0]["connection_config"] = {"prefix": "data/results/"}
    tree = CodeGenerator().generate(project(payload))
    main = tree["connection-check/environments/dev/main.tf"]
    if payload["resources"][0]["service_type"] == "athena":
        assert (
            'format("s3://%s/%s", module.target-resource.bucket_name, "data/results/")'
            in main
        )
        assert any("result_configuration {" in text for text in tree.values())
    else:
        assert (
            'format("%s/%s", module.target-resource.bucket_arn, "data/results")' in main
        )
        assert (
            sum(
                text.count('resource "aws_lakeformation_resource"')
                for text in tree.values()
            )
            == 1
        )
    preview = ConnectionPreviewer().preview_all(project(payload))[0]
    assert preview.issues and not preview.iam


def test_duplicate_location_connections_are_idempotent(payload):
    expected = CodeGenerator().generate(project(payload))
    payload["connections"] *= 2
    assert CodeGenerator().generate(project(payload)) == expected


def test_conflicting_locations_are_rejected(payload):
    other = deepcopy(payload["connections"][0])
    other["connection_config"] = {"prefix": "other"}
    payload["connections"].append(other)
    with pytest.raises(InvalidConnectionConfigError, match="one managed S3 location"):
        CodeGenerator().generate(project(payload))


def test_unconnected_external_location_is_retained(payload):
    payload["connections"] = []
    source = payload["resources"][0]
    field = "output_location" if source["service_type"] == "athena" else "resource_arn"
    source["config"][field] = (
        "s3://external/results/"
        if field == "output_location"
        else "arn:aws:s3:::external/data"
    )
    text = "\n".join(CodeGenerator().generate(project(payload)).values())
    assert source["config"][field] in text
    assert "managed-by-connection" not in text


def test_lake_formation_requires_an_unambiguous_role():
    payload = connection_architecture(
        resolve_spec(ServiceType.LAKE_FORMATION, ServiceType.S3, "registers", {})
    )
    payload["resources"][0]["config"]["use_service_linked_role"] = False
    with pytest.raises(InvalidConnectionConfigError, match="external access role"):
        CodeGenerator().generate(project(payload))
