"""Runtime-specific settings for managed EFS mounts."""

from app.models.connection_configs._metadata import ConnectionField
from app.models.connection_configs.storage import EfsLambdaMountConfig
from app.models.input_models._metadata import ValidationRule


class EfsClientMountConfig(EfsLambdaMountConfig):
    root_directory: str | None = ConnectionField(
        None,
        label="EFS directory",
        description="Defaults to a stable directory for this mount",
        validation=ValidationRule(pattern=r"^/[A-Za-z0-9_-]+$"),
    )
    local_mount_path: str = ConnectionField(
        "/mnt/efs",
        label="Mount path",
        validation=ValidationRule(pattern=r"^/mnt/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+$"),
    )


class EfsEc2MountConfig(EfsClientMountConfig):
    install_efs_utils: bool = ConnectionField(
        False,
        label="Install EFS helper",
        type="boolean",
        description="Install amazon-efs-utils using dnf/yum on Amazon Linux; otherwise the AMI must already include it",
    )


class EfsEcsMountConfig(EfsClientMountConfig):
    container_name: str | None = ConnectionField(
        None,
        label="Container name",
        description="Defaults to the ECS node name",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9_-]+$"),
    )


class EfsEksMountConfig(EfsClientMountConfig):
    claim_name: str = ConnectionField(
        "efs-data",
        label="Persistent volume claim",
        validation=ValidationRule(pattern=r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"),
    )
    namespace: str = ConnectionField(
        "default",
        label="Kubernetes namespace",
        description="The namespace must already exist",
        validation=ValidationRule(pattern=r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"),
    )
    node_role_arn: str = ConnectionField(
        ...,
        label="EC2 node role ARN",
        description="Role available to the EFS CSI node plugin on Linux EC2 workers",
        validation=ValidationRule(
            pattern=r"^arn:[^:]+:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+$"
        ),
    )

    @property
    def storage_identity(self) -> str:
        return self.container_name

    @property
    def container_name(self) -> str:
        return f"{self.namespace}/{self.claim_name}"
