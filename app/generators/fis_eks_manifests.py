"""AWS's namespace RBAC contract is exported for explicit manual application."""

from app.generators.hcl_renderer import Expr


def pod_access_manifests() -> list[dict]:
    name = Expr("var.fis_eks_pods.service_account")
    namespace = Expr("var.fis_eks_pods.namespace")
    metadata = {"name": name, "namespace": namespace}
    return [
        {"apiVersion": "v1", "kind": "ServiceAccount", "metadata": metadata},
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "Role",
            "metadata": metadata,
            "rules": [
                {
                    "apiGroups": [""],
                    "resources": ["configmaps"],
                    "verbs": ["get", "create", "patch", "delete"],
                },
                {
                    "apiGroups": [""],
                    "resources": ["pods"],
                    "verbs": ["create", "list", "get", "delete", "deletecollection"],
                },
                {
                    "apiGroups": [""],
                    "resources": ["pods/ephemeralcontainers"],
                    "verbs": ["update"],
                },
                {"apiGroups": [""], "resources": ["pods/exec"], "verbs": ["create"]},
                {"apiGroups": ["apps"], "resources": ["deployments"], "verbs": ["get"]},
            ],
        },
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "RoleBinding",
            "metadata": metadata,
            "subjects": [
                {"kind": "ServiceAccount", "name": name, "namespace": namespace},
                {
                    "kind": "Group",
                    "name": Expr("var.fis_eks_pods.kubernetes_group"),
                    "apiGroup": "rbac.authorization.k8s.io",
                },
            ],
            "roleRef": {
                "kind": "Role",
                "name": name,
                "apiGroup": "rbac.authorization.k8s.io",
            },
        },
    ]


def pod_access_guide(output_name: str) -> str:
    return f"""# EKS pod deletion prerequisites

Terraform creates an experiment template, role policy, and a cluster-owned access entry. It does not start experiments or apply Kubernetes objects. API_AND_CONFIG_MAP authentication is enabled when no mode is specified; enabling API authentication cannot be reversed. A shared principal has one access entry per cluster and receives the union of namespace bindings you apply. Import an existing externally managed entry into the generated cluster resource before applying instead of creating a duplicate.

After Terraform apply, configure kubectl for the connected cluster, verify its identity, and run these commands from the generated environment directory:

```sh
terraform output -json {output_name}_outputs | jq -r '.eks_pod_access_manifests' > fis-pod-access.yaml
kubectl apply -f fis-pod-access.yaml
terraform output -json {output_name}_outputs | jq '.eks_pod_target'
```

The namespace and Deployment must already exist. The manifests contain a ServiceAccount, namespace Role, and RoleBinding using AWS's documented FIS permissions, including pod creation/deletion, exec, ephemeral-container updates, and ConfigMap operations. These permissions cover the namespace, beyond the deployment selector, and apply to both the service account and the experiment role's Kubernetes group. Use a dedicated namespace and role when isolation is required. The deployment identity needs EKS access-entry management; applying RBAC requires appropriate Kubernetes administrator permissions.

Check running pod availability, orchestration-pod capacity, image pulls, admission policies, Kubernetes API reachability, and compatible security contexts. AWS requires Kubernetes 1.30 or newer and readOnlyRootFilesystem=false for its pod-action monitoring. Missing targets or an unavailable COUNT can fail; ALL follows current deployment scale. Pod deletion uses the pod's default termination grace period, stops all containers, and does not use eviction or respect PodDisruptionBudgets. Controllers may create replacements, but this connection does not verify recovery. Alarm stop conditions and fault logging remain unconfigured.

Delete the exported RBAC objects before removing the Terraform connection. Terraform destroy cannot revoke manually applied RoleBindings or service-account tokens. Shared access entries remain while another connected template uses that role; deleting/recreating an IAM role requires recreating its access entry. This integration targets regional EKS clusters with separately provisioned workloads and does not implement node-group termination, stress faults, or network faults.
"""
