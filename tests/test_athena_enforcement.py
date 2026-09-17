"""Workgroup enforcement is independent of an optional S3 result location."""

import pytest

from app.generators.athena_generator import AthenaGenerator
from app.models.input_models import ServiceType
from app.models.input_models.athena_config import AthenaConfig
from app.models.ir_models import ResourceInstanceIR


@pytest.mark.parametrize("enforce", [False, True])
def test_enforcement_without_output_location(enforce):
    instance = ResourceInstanceIR(
        name="queries",
        service_type=ServiceType.ATHENA,
        config=AthenaConfig(enforce_workgroup_configuration=enforce),
    )
    generator = AthenaGenerator()
    resource = generator.generate_resource_tf(instance)
    variables = generator.generate_variables_tf(instance)
    assert (
        "enforce_workgroup_configuration = var.enforce_workgroup_configuration"
        in resource
    )
    assert "result_configuration" not in resource
    assert 'variable "enforce_workgroup_configuration"' in variables
    assert f"default = {str(enforce).lower()}" in " ".join(variables.split())
