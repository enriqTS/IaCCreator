from app.generators.ecr_images import image_reference
from app.generators.hcl_renderer import Expr


def image_locals() -> dict:
    return {
        "registry_image_bindings": Expr(
            " { for key, binding in var.registry_images : key => merge(binding, { image = "
            + image_reference("binding")
            + " }) }"
        ),
        "registry_pull_roles": Expr(
            "{ for binding in values(var.registry_images) : sha256(binding.pull_role_arn) => binding.pull_role_arn... }"
        ),
        "registry_role_types": Expr(
            "{ for binding in values(var.registry_images) : sha256(binding.pull_role_arn) => binding.pull_role_type... }"
        ),
        "registry_containers": Expr(
            '{ for binding in values(local.registry_image_bindings) : "${binding.namespace}/${binding.deployment_name}/${binding.container_name}" => binding... }'
        ),
        "registry_workloads": Expr(
            '{ for binding in values(local.registry_image_bindings) : "${binding.namespace}/${binding.deployment_name}" => binding... }'
        ),
        "registry_image_patches": Expr("""{ for workload, bindings in local.registry_workloads : workload => {
    apiVersion = "apps/v1"
    kind = "Deployment"
    metadata = { namespace = bindings[0].namespace, name = bindings[0].deployment_name }
    spec = { template = { spec = { containers = [for name in sort(distinct([for binding in bindings : binding.container_name])) : { name = name, image = [for binding in bindings : binding.image if binding.container_name == name][0] }] } } }
  } }"""),
    }


def image_patch_guide(output_name: str) -> str:
    return f"""# ECR images for existing EKS Deployments

Terraform attaches image-pull policies to the explicitly configured external EC2 worker or Fargate pod execution roles. It does not create worker nodes, Fargate profiles, application credentials, image pull secrets, namespaces, Deployments, or Kubernetes resources. Each role must already be used by the compute that runs the selected workload. Trust guards check an explicit Allow for the chosen compute service; trust conditions, explicit denies, profile selection, role association, network access, and scheduling remain your responsibility. Existing role policies and permission boundaries are preserved; a preexisting wildcard ECR policy still permits broader pulls.

After Terraform apply, configure kubectl for the connected cluster and verify its identity against these outputs from the generated environment directory:

```sh
terraform output -json {output_name}_outputs | jq '.ecr_image_target'
terraform output -json {output_name}_outputs | jq '.ecr_image_bindings'
terraform output -json {output_name}_outputs | jq '.ecr_image_patches | keys'
```

For an output key such as `default/web`, export and review its patch, then use the matching namespace and Deployment:

```sh
terraform output -json {output_name}_outputs | jq -r '.ecr_image_patches["default/web"]' > ecr-image-patch.yaml
kubectl get deployment web --namespace default -o json | jq '.spec.template.spec.containers | map({{name, image}})'
kubectl patch deployment web --namespace default --type strategic --patch-file ecr-image-patch.yaml --dry-run=server -o yaml
kubectl patch deployment web --namespace default --type strategic --patch-file ecr-image-patch.yaml
```

Replace the example key and Deployment with the effective output values. Every selected application container must already exist: strategic merge matches containers by name and adds a container if the name is absent. Verify the names and review the server dry run before executing the final command. These are partial strategic merge patches, so do not use `kubectl apply` or a JSON merge patch. The patch contains only selected regular-container images; other containers, init containers, environment, ports, storage, logging, service accounts, replicas, selectors, and existing imagePullPolicy remain unchanged.

Push compatible images before patching. No image lookup, build, publication, token retrieval, or scanning verification is generated. A changed pod template can roll out new pods according to the Deployment's existing strategy; the connection does not monitor rollout health. Reapplying an unchanged mutable tag does not force a rollout, and existing imagePullPolicy still controls caching. Prefer immutable tags or digests when releases require explicit image changes. Kubernetes API access/RBAC and registry/S3 layer network access are prerequisites.

Repository grants cover every user of the configured role, beyond the named Deployment. A workload spanning several worker roles needs a matching image connection for each role. Fargate pods use the profile's pod execution role, which is distinct from EC2 node roles and application IRSA/Pod Identity roles. Fargate trust conditions must allow the matching cluster/profile. Cross-account and cross-Region pulls are unsupported by this connection.

Removing the connection removes its IAM grants but does not restore manually patched workloads. Update your workload source of truth and images before removing repositories or policies. Coordinate these patches with Helm/GitOps owners so controllers do not revert them; the generated patches are not complete application manifests.
"""
