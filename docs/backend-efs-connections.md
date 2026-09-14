# EFS runtime connections

EFS `mounts` connections support Lambda, EC2, ECS, and EKS. EC2/ECS/EKS share an access-point builder; each binding owns an EFS access point and a separate default directory. Explicit root directories allow intentional sharing. UID/GID and read/write access are typed connection fields. Conflicting or overlapping paths within a container are rejected.

Access points and mount targets belong to the EFS module. Filesystem and access-point references flow into the consuming module through outputs that wait for mount targets. Consumers own runtime permissions and configuration. Filesystem-scoped IAM grants permit ClientMount and, for writable connections, ClientWrite. Network rules must permit TCP 2049 to reachable mount targets.

## EC2

EC2 requires subnet and security-group placement. Generated Bash bootstrap mounts each access point using TLS and IAM, records the mount in fstab, and runs configured shell user data afterward. The AMI must include `amazon-efs-utils`, or the connection must explicitly enable installation through dnf/yum. Cloud-config and multipart user data are not supported with generated mounts.

Mounts reuse the instance role/profile used by secret connections. Mount user-data changes replace the instance so bootstrap runs again; preserve application data outside the instance. Existing EFS directory data remains independent of instance replacement.

## ECS

ECS requires subnet and security-group placement. The connection emits native task volumes with transit encryption and access-point IAM authorization, and grants the task role filesystem access. It merges mount points into the named container while preserving unrelated mount points and secret bindings. Missing containers fail a Terraform precondition.

Unspecified launch type defaults to Fargate for mounted tasks. Use Linux Fargate platform 1.4 or newer, or an EFS-capable EC2 agent. Capacity, image availability, and network connectivity remain deployment prerequisites.

## EKS

EKS manages the `aws-efs-csi-driver` add-on by default; disable `manage_efs_csi_driver` when another system owns the driver. `efs_csi_addon_version` optionally pins its version. Each connection requires the external Linux EC2 worker role ARN used by the CSI node plugin. The connection attaches a filesystem policy to that role; workers must expose the role credentials to the plugin. This connection does not support Fargate, Windows, or Hybrid Nodes.

Terraform creates static access points and exports `efs_storage_manifests` and `efs_workload_mounts`. It does not use the Kubernetes provider. The generated EKS module includes `EFS-MOUNTS.md` with commands to export and apply PV/PVC YAML after Terraform apply, then merge the volume bindings into application workloads. Namespaces, workers, and workloads must already exist or be deployed separately.

PV/PVC bindings use an empty storage class, explicit claim/volume references, and Retain reclaim policy. Capacity is a Kubernetes binding placeholder, not an EFS quota. Both access modes use ReadWriteMany because the [EFS CSI driver](https://github.com/kubernetes-sigs/aws-efs-csi-driver/blob/master/pkg/driver/node.go) accepts writer capabilities; read-only access is enforced by CSI/mount flags, workload bindings, and omission of ClientWrite permission. Static provisioning needs no CSI CreateAccessPoint/DeleteAccessPoint permissions.

Changing the workload mount path preserves the claim's access-point identity and default directory. Stop workloads and remove their Kubernetes storage objects before destroying the Terraform access points. Deleting an access point does not delete its EFS directory contents. See the [AWS EKS EFS CSI guide](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html) for cluster prerequisites.
