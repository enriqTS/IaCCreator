"""EKS owns its CSI add-on, node-role permissions, and renderable storage manifests."""

import hashlib

from app.generators.eks_efs_manifests import storage_manifests, workload_mount
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.efs import EfsEksMountConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier
from app.services.connection_handlers.efs_client_mounts import (
    EfsClientMounts,
    has_placement,
    reject_mount,
)


class EfsEksMountHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Requires Linux EC2 workers and EFS CSI node-plugin access to the configured node role credentials. TCP 2049 reachability and worker capacity are separate. Apply the exported PV/PVC manifests and add the exported volume bindings to workloads; Terraform does not deploy Kubernetes objects. Fargate, Windows, and Hybrid Nodes are not supported by this connection.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        cluster = self._find_instance(connection.target_name, project)
        if not has_placement(cluster.name, "subnet_ids", ServiceType.SUBNET, project):
            reject_mount(connection, "EKS requires subnet placement")
        mounts, result = EfsClientMounts().build(connection, project, EfsEksMountConfig)
        claims = [mount.container for mount in mounts]
        if len(set(claims)) != len(claims):
            reject_mount(
                connection, "Each namespace and claim name must identify one EFS mount"
            )
        dependencies = []
        if cluster.config.manage_efs_csi_driver:
            attrs = {
                "cluster_name": Expr(f"aws_eks_cluster.{cluster.name}.name"),
                "addon_name": "aws-efs-csi-driver",
            }
            if cluster.config.efs_csi_addon_version:
                attrs["addon_version"] = cluster.config.efs_csi_addon_version
            result.resources.append(
                self._resource(
                    cluster.name,
                    "efs_csi.tf",
                    self._renderer.render_resource("aws_eks_addon", "efs_csi", attrs),
                )
            )
            dependencies.append("aws_eks_addon.efs_csi")
        roles = sorted({mount.config.node_role_arn for mount in mounts})
        for role in roles:
            name = "efs_node_" + hashlib.sha256(role.encode()).hexdigest()[:12]
            result.inputs.append(
                ModuleInput(
                    module=cluster.name,
                    name=name,
                    value=self._renderer.render_expression(role),
                    description="External EC2 worker role",
                )
            )
            statements = []
            for mount in mounts:
                if mount.config.node_role_arn != role:
                    continue
                actions = ["elasticfilesystem:ClientMount"]
                if mount.config.access == "write":
                    actions.append("elasticfilesystem:ClientWrite")
                statements.append(
                    {
                        "Effect": "Allow",
                        "Action": actions,
                        "Resource": Expr(f"var.{mount.name}_filesystem_arn"),
                    }
                )
            result.resources.append(
                self._resource(
                    cluster.name,
                    f"{name}.tf",
                    self._renderer.render_resource(
                        "aws_iam_role_policy",
                        name,
                        {
                            "name_prefix": "efs-node-mounts-",
                            "role": Expr(
                                f'element(reverse(split("/", var.{name})), 0)'
                            ),
                            "policy": self._renderer.render_json_policy(
                                {"Version": "2012-10-17", "Statement": statements}
                            ),
                        },
                    ),
                )
            )
            dependencies.append(f"aws_iam_role_policy.{name}")
        manifests = [
            manifest
            for mount in mounts
            for manifest in storage_manifests(mount.name, mount.config)
        ]
        body = (
            "locals {\n  efs_storage_manifests = "
            + self._renderer.render_expression(manifests)
            + "\n}\n"
        )
        result.resources.append(self._resource(cluster.name, "efs_manifests.tf", body))
        result.outputs.extend(
            [
                ModuleOutput(
                    module=cluster.name,
                    name="efs_storage_manifests",
                    value='join("\\n---\\n", [for manifest in local.efs_storage_manifests : yamlencode(manifest)])',
                    description="Apply these PV/PVC manifests to the cluster after Terraform",
                    depends_on=dependencies,
                ),
                ModuleOutput(
                    module=cluster.name,
                    name="efs_workload_mounts",
                    value=self._renderer.render_expression(
                        [workload_mount(mount.name, mount.config) for mount in mounts]
                    ),
                    description="Volume and volumeMount entries to merge into workloads",
                    depends_on=dependencies,
                ),
            ]
        )
        guide = f"""# EFS storage for {cluster.name}

This connection supports Linux EC2 workers with the EFS CSI node plugin using the configured node role. It does not deploy worker nodes or application workloads. The CSI controller needs no dynamic provisioning permissions: Terraform owns the access points and the manifests use static provisioning.

After Terraform apply, configure kubectl for this cluster and run these commands from the generated environment directory:

```sh
terraform output -json {safe_identifier(cluster.name)}_outputs | jq -r '.efs_storage_manifests' > efs-storage.yaml
kubectl apply -f efs-storage.yaml
terraform output -json {safe_identifier(cluster.name)}_outputs | jq '.efs_workload_mounts'
```

Merge the matching volume and volumeMount entries into your workload pod specification in the claim namespace. Namespaces must already exist. Ensure workers can reach an EFS mount target on TCP 2049 and that the CSI node plugin can obtain the configured role credentials. EFS storage capacity values satisfy Kubernetes binding requirements and do not impose a 5 GiB EFS quota.

If the CSI driver is already managed elsewhere, disable manage_efs_csi_driver on the EKS node. Do not install a second driver. Stop workloads and delete the Kubernetes storage objects before removing their Terraform-managed access points. Retain reclaim policy preserves storage; deleting an access point does not remove its EFS directory data.
"""
        result.resources.append(self._resource(cluster.name, "EFS-MOUNTS.md", guide))
        return result
