"""Static Kubernetes storage manifests reference Terraform-owned EFS access points."""

from app.generators.hcl_renderer import Expr
from app.models.connection_configs.efs import EfsEksMountConfig


def storage_manifests(identifier: str, config: EfsEksMountConfig) -> list[dict]:
    name = identifier.replace("_", "-")
    read_only = config.access == "read"
    # The EFS CSI driver accepts writer capabilities even for read-only mounts.
    modes = ["ReadWriteMany"]
    return [
        {
            "apiVersion": "v1",
            "kind": "PersistentVolume",
            "metadata": {"name": name},
            "spec": {
                "capacity": {"storage": "5Gi"},
                "volumeMode": "Filesystem",
                "accessModes": modes,
                "persistentVolumeReclaimPolicy": "Retain",
                "storageClassName": "",
                "claimRef": {"name": config.claim_name, "namespace": config.namespace},
                "mountOptions": ["tls", "iam"] + (["ro"] if read_only else []),
                "csi": {
                    "driver": "efs.csi.aws.com",
                    "volumeHandle": Expr(
                        f'"${{var.{identifier}_filesystem_id}}::${{var.{identifier}_access_point_id}}"'
                    ),
                    "readOnly": read_only,
                },
            },
        },
        {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {"name": config.claim_name, "namespace": config.namespace},
            "spec": {
                "accessModes": modes,
                "storageClassName": "",
                "volumeName": name,
                "resources": {"requests": {"storage": "5Gi"}},
            },
        },
    ]


def workload_mount(identifier: str, config: EfsEksMountConfig) -> dict:
    name = identifier.replace("_", "-")
    return {
        "namespace": config.namespace,
        "claim_name": config.claim_name,
        "volume": {
            "name": name,
            "persistentVolumeClaim": {"claimName": config.claim_name},
        },
        "volumeMount": {
            "name": name,
            "mountPath": config.local_mount_path,
            "readOnly": config.access == "read",
        },
    }
