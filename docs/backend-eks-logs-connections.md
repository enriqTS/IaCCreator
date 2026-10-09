# EKS control-plane logging connections

`EKS → CloudWatch` (`logs_to`) enables selected control-plane logs and manages their required destination through the existing CloudWatch node. `EksLogsConfig` exposes five boolean selections: `api`, `audit`, `authenticator`, `controllerManager`, and `scheduler`. All default to true. The backend requires real booleans and at least one selected type. [AWS documents these native log types and their fixed destination naming](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html).

## Ownership and ordering

The cluster module exports `control_plane_log_group_name` as `/aws/eks/${var.cluster_name}/cluster`. This output depends only on the cluster input, so the CloudWatch module can use it before the cluster exists. The connection overrides the group's `log_group_name` argument; clear a manually configured name or provide the matching native name. Changing the cluster input follows through to the log-group name without copying identifiers. Retention and tags remain configured on the CloudWatch node.

The group module exports `eks_control_plane_destination`, a typed object containing its actual ARN, class, and customer-key setting. The cluster consumes this object in lifecycle preconditions, so creation waits for the group before enabling `enabled_cluster_log_types`. The input-only name output prevents a dependency cycle even though references travel in both directions. Module-wide `depends_on` is unnecessary. Terraform's native logging argument is described in the [AWS provider documentation](https://github.com/hashicorp/terraform-provider-aws/blob/main/website/docs/r/eks_cluster.html.markdown).

`EksLogsHandler` owns the cluster's `control_plane_logs.tf` identity lookups. The CloudWatch node owns its group resource; the connection contributes an input and output to that module, without writing a resource file there. Repeated connections must have the same destination and effective selections and produce one set of inputs and outputs. Each cluster requires a dedicated group; multiple clusters cannot share one node, and one cluster cannot select multiple groups.

## Guards and permissions

Backend validation rejects conflicting bindings, manual name conflicts, unsupported group classes, customer-managed KMS keys, and effective Region mismatches, including environment overrides. Four Terraform preconditions check the native cluster-name syntax, the exact group ARN in the deployment partition/Region/account, Standard class with default encryption, and nonempty unique supported log types. These checks also cover manually changed module inputs.

EKS delivers logs through its AWS-owned `AWSServiceRoleForAmazonEKS`, separate from the externally configured cluster role. The connection creates no delivery role, inline IAM policy, resource policy, node agent, or Kubernetes resource. AWS creates the service-linked role when needed; the deployment identity needs appropriate creation permissions. [AWS describes the role lifecycle and restricts edits to its permissions](https://docs.aws.amazon.com/eks/latest/userguide/using-service-linked-roles-eks.html).

This connection supports default CloudWatch encryption only. Both diagram-owned KMS connections and external `kms_key_id` settings are rejected: adding caller permissions for the AWS-owned service-linked role requires separate key-policy support. Existing unrelated KMS connections retain their behavior. Pod/application logs, Container Insights, Fluent Bit, and node agents require independent collection and are outside this relationship.

## Deployment prerequisites

Supply the cluster's external IAM role with the required trust and permissions, plus suitable cluster networking. Logging configuration updates require up to five available IP addresses per subnet. Delivery is best effort; CloudWatch ingestion and storage charges apply. Existing groups created by EKS must be imported into the generated CloudWatch resource address before applying, rather than creating a second resource with the same name. These operational details follow the [EKS logging guide](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html).

The connection composes with managed subnet placement, EFS CSI/storage manifests, EKS managed Prometheus scrapers, and Grafana CloudWatch queries. Logging does not alter endpoint exposure or authentication; other connections retain ownership of those settings.

## Verification

`tests/test_eks_logs_connections.py` covers typed defaults/selections, deterministic duplicates, ownership conflicts, native guards, matching names, retention/tags, effective Regions, standalone compatibility, and previews. Terraform console checks evaluate invalid native overrides. Generated projects pass provider validation and plan-graph construction for plain, audit-only, duplicate, multiple-cluster, regional, managed-network, and combined EFS/Prometheus/Grafana architectures. API schema tests verify dynamic discovery of all five boolean fields. No live AWS deployment or ingestion test is performed.
