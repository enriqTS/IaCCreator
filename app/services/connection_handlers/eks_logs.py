"""Native EKS log naming and dependency guards preserve log-group ownership."""

import json

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.generators.eks_logs import render_eks_log_resources
from app.models.connection_configs.eks_logs import EksLogsConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_references import managed_key


class EksLogsHandler(BaseConnectionHandler):
    def _selection(self, connection: ConnectionIR, project: ProjectIR) -> EksLogsConfig:
        peers = [
            item
            for item in project.connections
            if item.source_name == connection.source_name
            and item.source_service == ServiceType.EKS
            and item.target_service == ServiceType.CLOUDWATCH
            and item.connection_type == "logs_to"
        ]
        owners = {
            item.source_name
            for item in project.connections
            if item.target_name == connection.target_name
            and item.source_service == ServiceType.EKS
            and item.target_service == ServiceType.CLOUDWATCH
            and item.connection_type == "logs_to"
        }
        source = self._find_instance(connection.source_name, project)
        group = self._find_instance(connection.target_name, project)
        request = EksLogsConfig.model_validate(connection.connection_config)
        errors = []
        if len({item.target_name for item in peers}) > 1 or len(owners) > 1:
            errors.append(
                {
                    "loc": ("target",),
                    "msg": "Each EKS cluster requires one dedicated control-plane log group",
                }
            )
        if any(
            EksLogsConfig.model_validate(item.connection_config) != request
            for item in peers
        ):
            errors.append(
                {
                    "loc": ("connection_config",),
                    "msg": "Repeated EKS logging connections must select the same log types",
                }
            )
        cluster_name = source.config.cluster_name or source.terraform_variables.get(
            "cluster_name"
        )
        if (
            group.config.log_group_name
            and group.config.log_group_name != f"/aws/eks/{cluster_name}/cluster"
        ):
            errors.append(
                {
                    "loc": ("log_group_name",),
                    "msg": "Remove the manually configured log-group name or match /aws/eks/<cluster-name>/cluster",
                }
            )
        if group.config.log_group_class not in (None, "STANDARD"):
            errors.append(
                {
                    "loc": ("log_group_class",),
                    "msg": "EKS control-plane logging supports Standard log groups",
                }
            )
        if group.config.kms_key_id or managed_key(group.name, project):
            errors.append(
                {
                    "loc": ("kms_key_id",),
                    "msg": "Customer-managed EKS log encryption requires separate service-linked-role key-policy support",
                }
            )
        if errors:
            raise InvalidConnectionConfigError(
                source.name, group.name, connection.connection_type, errors
            )
        for environment in project.environments:
            override = environment.variables.get("region")
            source_region = (
                override
                or source.provider_region
                or project.global_config.provider_region
            )
            target_region = (
                override
                or group.provider_region
                or project.global_config.provider_region
            )
            if source_region != target_region:
                raise CrossRegionConnectionError(
                    source.name,
                    source_region,
                    group.name,
                    target_region,
                    connection.connection_type,
                )
        return request

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        request = self._selection(connection, project)
        name = connection.source_name
        target = connection.target_name
        self._find_instance(name, project).config._control_plane_logs = True
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=target,
                    name="log_group_name",
                    value=f"module.{name}.control_plane_log_group_name",
                    description="EKS-mandated control-plane log group name",
                ),
                ModuleInput(
                    module=name,
                    name="enabled_cluster_log_types",
                    type="list(string)",
                    value=json.dumps(request.enabled_types()),
                    description="Selected native EKS control-plane log types",
                ),
                ModuleInput(
                    module=name,
                    name="control_plane_log_group",
                    type="object({ arn = string, log_group_class = string, kms_key_arn = string })",
                    value=f"module.{target}.eks_control_plane_destination",
                    description="Ready native EKS control-plane log destination",
                ),
            ],
            outputs=[
                self._output(
                    name,
                    "control_plane_log_group_name",
                    '"/aws/eks/${var.cluster_name}/cluster"',
                    "Required log-group name independent of cluster creation",
                ),
                self._output(
                    target,
                    "eks_control_plane_destination",
                    f'{{ arn = aws_cloudwatch_log_group.{target}.arn, log_group_class = aws_cloudwatch_log_group.{target}.log_group_class, kms_key_arn = aws_cloudwatch_log_group.{target}.kms_key_id == null ? "" : aws_cloudwatch_log_group.{target}.kms_key_id }}',
                    "Native log-group identity and settings for EKS logging",
                ),
            ],
            resources=[
                self._resource(
                    name, "control_plane_logs.tf", render_eks_log_resources()
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        self._selection(connection, project)
        return [
            ConnectionIssue(
                severity="warning",
                message="EKS enables the selected control-plane logs after the connected Standard group is ready. Its required /aws/eks/<cluster-name>/cluster name follows the cluster input; retention and tags belong to CloudWatch. Delivery uses AWS's service-linked role, which is separate from the external cluster role. The deployment identity must manage EKS logging, CloudWatch groups, and initial service-linked-role creation; cluster-role trust/permissions and network placement remain prerequisites. Logging updates need up to five free IP addresses in each cluster subnet. Delivery is best effort and CloudWatch ingestion/storage charges apply. Import an already existing EKS log group into the generated Terraform address before applying. Customer-managed KMS keys, pod/application logs, Container Insights, and node agents are outside this connection.",
            )
        ]
