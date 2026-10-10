# ECR images for existing EKS Deployments

ECR → EKS (`runs_image`) exports partial strategic merge patches for selected regular containers in existing Kubernetes Deployments. Terraform owns the repository references and external compute-role pull grants. Kubernetes changes remain manual, following the existing EKS manifest workflow.

## Connection settings

| Field | Behavior |
|---|---|
| `namespace` | Existing namespace; defaults to `default`. |
| `deployment_name` | Required existing Deployment name. |
| `container_name` | Existing regular application container; defaults to `app`. |
| `image_version` | Literal Docker tag or lowercase `sha256:<64 hex characters>` digest; defaults to `latest`. |
| `pull_role_arn` | Required existing EC2 worker role or Fargate pod execution role already used by the workload's compute. |
| `pull_role_type` | `node` (default) or `fargate`; validates the selected compute trust principal. |

Namespace/container names use lowercase DNS labels up to 63 characters. Deployment names use bounded DNS subdomains up to 253 characters, with labels up to 63 characters. Repository names follow private ECR naming rules. Images use native `<repository_url>:<tag>` or `<repository_url>@<digest>` references; no image lookup, build, publication, scanning verification, or authorization-token retrieval is generated.

## Pull roles and references

EKS currently models a cluster, with externally provisioned workers and profiles. The configured pull role must already serve the workload. EC2 nodes use their instance role; Fargate uses its profile's pod execution role. The cluster role is rejected, and no grants or annotations are added to application IRSA/Pod Identity roles. This edge does not create nodes, profiles, access entries, application credentials, or Kubernetes image-pull secrets.

Each external role receives one cluster-owned inline policy with `ecr:GetAuthorizationToken` on its required wildcard and `ecr:BatchCheckLayerAvailability`, `ecr:GetDownloadUrlForLayer`, and `ecr:BatchGetImage` on the sorted, distinct native repository ARNs used by that role's bindings. Unique policy name prefixes allow several clusters to share an external role without replacing each other's policies. Grants apply to all users of a role, beyond the selected Deployment. Existing policies and permission boundaries are preserved; any preexisting wildcard pull grant still permits broader access. Node add-on image permissions and other compute prerequisites remain external.

The repository exports native name, ARN, and URL references into a typed `registry_images` map in the EKS module. SHA-256 identities group compute roles and bindings deterministically. Identical duplicate edges are idempotent. Several containers can use different repositories, and one repository/role can serve several workloads or clusters. A workload spanning multiple worker roles needs an image connection for each role. A Deployment container must have one repository/version across its roles, and a role must have one compute type across connected clusters.

The backend validates names, image selectors, repository ownership, subnet placement, and effective Regions in every environment. Pending managed subnet placement is supported; a global environment Region override can align nodes. Terraform guards verify native cluster/repository identities against the deployment account, partition, and Region, valid workload settings, consistent images/compute types, and full external-role ARNs, including paths. Role lookup guards require an explicit Allow for `sts:AssumeRole` by `ec2.amazonaws.com` or `eks-fargate-pods.amazonaws.com`, matching the selected type. String/list trust actions and principals and singleton/list statements are supported. This is a prerequisite check, not a complete trust-policy evaluator: trust conditions, explicit denies, worker/profile association, Fargate namespace selection, and cluster access remain separately configured. Cross-account and cross-Region pulls are unsupported.

## Manual patches and lifecycle

The EKS module exports `ecr_image_target` with native cluster identity, `ecr_image_bindings` with effective image/role metadata, and `ecr_image_patches` as a map of YAML strings keyed by `<namespace>/<deployment>`. Outputs depend on the cluster and ready pull policies. Each Deployment patch contains only its metadata and selected container names/images, with repeated role bindings collapsed to one image entry.

Generated `ECR-IMAGES.md` explains output extraction, cluster/container verification, server dry runs, and explicit `kubectl patch --type strategic --patch-file` commands. These are partial patches; `kubectl apply` and JSON merge patches are inappropriate. Existing container fields, unselected regular/init containers, volumes, secrets, logging, service accounts, replicas, selectors, and imagePullPolicy are preserved by Kubernetes strategic merge semantics. The selected container must already exist: a mismatched name would add a container. Verify names and review the dry run before patching; generation cannot inspect live Kubernetes objects.

Push compatible images before applying patches. Changing the pod template can roll out pods according to the existing Deployment strategy, which this connection does not monitor. An unchanged mutable tag does not force rollout, and existing imagePullPolicy governs caching. Kubernetes RBAC/API reachability, registry/S3 layer network access, and compute capacity remain prerequisites. Keep Helm/GitOps workload definitions in sync. Removing the edge revokes only its Terraform-managed grants and does not restore manually patched workloads; update workloads before removing repositories or policies.

This connection composes with managed subnet placement, EKS control-plane logs, Prometheus collection, EFS CSI/static-storage manifests, and FIS access/RBAC exports. It does not alter authentication mode, cluster access, or observability/storage settings on its own. `ecr_images.py` and `models/ecr_image.py` share native identity, image-selector, reference, and pull-policy rules with ECR → ECS.

## Validation

`tests/test_ecr_eks_connections.py` covers typed fields, property-based repository/workload names, tags/digests, multi-role/container/cluster sharing, deterministic duplicates, backend conflicts, actual Terraform guard/trust evaluation, evaluated YAML patches, exact role-filtered IAM grants, and twelve cached-provider validation/dependency-graph projects. API tests verify schema discovery. ECR → ECS regressions verify the shared helpers. Checks do not apply Kubernetes patches, execute deployments, retrieve tokens, or contact AWS.

References: [AWS ECR images in EKS](https://docs.aws.amazon.com/AmazonECR/latest/userguide/ECR_on_EKS.html), [EKS node roles](https://docs.amazonaws.cn/en_us/eks/latest/userguide/create-node-role.html), [EKS Fargate pod execution roles](https://docs.aws.amazon.com/eks/latest/userguide/pod-execution-role.html), [Kubernetes strategic merge patches](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/update-api-object-kubectl-patch/), [Kubernetes image pull behavior](https://kubernetes.io/docs/concepts/containers/images/), and [Terraform IAM role lookup](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_role).
