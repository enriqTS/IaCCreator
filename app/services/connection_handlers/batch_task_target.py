"""Prepare generated Batch queues for event and workflow submissions."""

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR, ResourceInstanceIR


def prepare_batch_target(
    connection: ConnectionIR,
    project: ProjectIR,
    target: ResourceInstanceIR,
    definition_name: str,
) -> None:
    definition = next(
        (
            instance
            for module in project.modules
            for instance in module.instances
            if instance.name == definition_name
        ),
        None,
    )
    if (
        definition is None
        or definition.service_type != ServiceType.BATCH_JOB_DEFINITION
    ):
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [
                {
                    "loc": ("job_definition_name",),
                    "msg": "Select a Batch job definition node in this diagram",
                }
            ],
        )
    if (
        target.config.batch_compute_environment_type != "UNMANAGED"
        or not target.config.service_role_arn
    ):
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [
                {
                    "loc": ("batch_compute_environment_type",),
                    "msg": "Batch targets require an unmanaged compute environment, a service role, and external capacity",
                }
            ],
        )
    if not target.config.compute_environment_name:
        target.config.compute_environment_name = connection.target_name.replace(
            "-", "_"
        )
    if not target.config.job_queue_name:
        target.config.job_queue_name = f"{connection.target_name}-queue"
