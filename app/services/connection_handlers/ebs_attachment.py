"""The volume module owns its EC2 attachment and inherits the instance's zone."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.storage import EbsAttachmentConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class EbsAttachmentHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The volume is attached as a block device; filesystem formatting and mounting must be configured in the guest OS. Its Availability Zone follows the connected instance.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        volume, instance = connection.source_name, connection.target_name
        peers = [
            item
            for item in project.connections
            if item.source_service == ServiceType.EBS
            and item.target_service == ServiceType.EC2
            and item.connection_type == "attaches"
        ]
        device = EbsAttachmentConfig.model_validate(
            connection.connection_config
        ).device_name
        bindings = {
            (
                item.target_name,
                EbsAttachmentConfig.model_validate(item.connection_config).device_name,
            )
            for item in peers
            if item.source_name == volume
        }
        conflicts = {
            item.source_name
            for item in peers
            if item.target_name == instance
            and EbsAttachmentConfig.model_validate(item.connection_config)
            .device_name.removeprefix("/dev/")
            .removeprefix("xvd")
            .removeprefix("sd")
            == device.removeprefix("/dev/").removeprefix("xvd").removeprefix("sd")
        }
        if len(bindings) != 1 or len(conflicts) != 1:
            raise InvalidConnectionConfigError(
                volume,
                instance,
                connection.connection_type,
                [
                    {
                        "loc": ("device_name",),
                        "msg": "Each EBS volume requires one instance/device binding, and each instance device requires one volume",
                    }
                ],
            )
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=volume,
                    name="attached_instance_id",
                    value=f"module.{instance}.instance_id",
                    description="Instance receiving this volume",
                ),
                ModuleInput(
                    module=volume,
                    name="availability_zone",
                    value=f"module.{instance}.availability_zone",
                    description="Place the volume in the instance Availability Zone",
                ),
            ],
            resources=[
                self._resource(
                    volume,
                    "attachment.tf",
                    self._renderer.render_resource(
                        "aws_volume_attachment",
                        "instance",
                        {
                            "device_name": device,
                            "volume_id": Expr(f"aws_ebs_volume.{volume}.id"),
                            "instance_id": Expr("var.attached_instance_id"),
                        },
                    ),
                )
            ],
        )
