"""Reusable single-bucket location references with explicit consumer ownership."""

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.storage import S3LocationConfig
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class S3LocationHandler(BaseConnectionHandler):
    def __init__(self, input_name: str, uri: bool, permission_note: str) -> None:
        super().__init__()
        self._input_name = input_name
        self._uri = uri
        self._permission_note = permission_note

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [ConnectionIssue(severity="warning", message=self._permission_note)]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        locations = {
            (
                item.target_name,
                S3LocationConfig.model_validate(item.connection_config).prefix.rstrip(
                    "/"
                ),
            )
            for item in project.connections
            if item.source_name == connection.source_name
            and item.connection_type == connection.connection_type
        }
        if len(locations) != 1:
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("prefix",),
                        "msg": "This resource supports one managed S3 location",
                    }
                ],
            )
        bucket, prefix = next(iter(locations))
        if self._uri:
            path = self._renderer.render_expression(prefix + "/" if prefix else "")
            value = f'format("s3://%s/%s", module.{bucket}.bucket_name, {path})'
        else:
            value = f"module.{bucket}.bucket_arn"
            if prefix:
                value = f'format("%s/%s", {value}, {self._renderer.render_expression(prefix)})'
        source = self._find_instance(connection.source_name, project)
        setattr(source.config, self._input_name, "managed-by-connection")
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source.name,
                    name=self._input_name,
                    value=value,
                    description="Location in a managed S3 bucket",
                )
            ]
        )


class LakeFormationS3Handler(S3LocationHandler):
    def __init__(self) -> None:
        super().__init__(
            "resource_arn",
            False,
            "Lake Formation registration uses its configured service-linked or external role. External-role S3 permissions and encrypted-bucket KMS permissions must be supplied by the role/key owners; catalog grants remain separate.",
        )

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        source = self._find_instance(connection.source_name, project)
        if not source.config.use_service_linked_role and not source.config.role_arn:
            raise InvalidConnectionConfigError(
                source.name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("role_arn",),
                        "msg": "Lake Formation requires a service-linked role or an external access role",
                    }
                ],
            )
        if source.config.use_service_linked_role and source.config.role_arn:
            raise InvalidConnectionConfigError(
                source.name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("role_arn",),
                        "msg": "Choose either the service-linked role or an external access role",
                    }
                ],
            )
        return super().handle(connection, project)
