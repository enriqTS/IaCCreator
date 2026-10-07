"""Grafana queries require one enforced result location with a concrete prefix."""

import re

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.grafana_athena import RESULT_LOCATION_PATTERN
from app.models.connection_configs.storage import S3LocationConfig
from app.models.input_models import ServiceType
from app.models.ir_models import ProjectIR, ResourceInstanceIR


def validate_athena_results(
    workspace: str, target: ResourceInstanceIR, project: ProjectIR
) -> None:
    locations = {
        (
            item.target_name,
            S3LocationConfig.model_validate(item.connection_config).prefix.rstrip("/"),
        )
        for item in project.connections
        if item.source_name == target.name
        and item.source_service == ServiceType.ATHENA
        and item.target_service == ServiceType.S3
        and item.connection_type == "stores_results"
    }
    field, message = (
        "output_location",
        "Grafana requires a concrete S3 result prefix ending in /, configured on Athena or through one Athena → S3 connection",
    )
    if not target.config.enforce_workgroup_configuration:
        field, message = (
            "enforce_workgroup_configuration",
            "Grafana requires enforced workgroup result settings",
        )
    elif locations:
        if len(locations) == 1:
            _, prefix = next(iter(locations))
            if re.fullmatch(RESULT_LOCATION_PATTERN, f"s3://example-bucket/{prefix}/"):
                return
    elif target.config.output_location and re.fullmatch(
        RESULT_LOCATION_PATTERN, target.config.output_location
    ):
        return
    raise InvalidConnectionConfigError(
        workspace, target.name, "queries", [{"loc": (field,), "msg": message}]
    )
