"""Pod targets consume ready cluster access while role outputs remain input-only."""

from app.generators.eks_fis_access import render_experiment_access
from app.generators.fis_eks import render_eks_fault_policy
from app.generators.fis_eks_manifests import pod_access_guide, pod_access_manifests
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier
from app.services.connection_handlers.fis_eks_bindings import (
    experiment_role_sources,
    resolve_eks_fault,
)


class FisEksHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        binding = resolve_eks_fault(connection, project)
        peers = [
            item
            for item in project.connections
            if item.source_name == connection.source_name
            and item.source_service == ServiceType.FAULT_INJECTION_SIMULATOR
            and item.target_service == ServiceType.EKS
            and item.connection_type == "targets"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        source, target = connection.source_name, binding.target
        self._find_instance(source, project).config._target_service = ServiceType.EKS
        cluster_config = self._find_instance(target, project).config
        if cluster_config.authentication_mode is None:
            cluster_config.authentication_mode = "API_AND_CONFIG_MAP"
        settings = {
            **binding.settings.model_dump(),
            "service_account": binding.service_account,
            "kubernetes_group": binding.kubernetes_group,
        }
        roles = {
            key: Expr(f"module.{owner}.fis_experiment_role")
            for key, owner in experiment_role_sources(target, project).items()
        }
        manifests = (
            "locals {\n  fis_eks_manifests = "
            + self._renderer.render_expression(pod_access_manifests(), depth=2)
            + "\n}\n"
        )
        cluster = f"aws_eks_cluster.{target}"
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source,
                    name="fis_eks_cluster",
                    type="object({ arn = string, name = string, version = string, authentication_mode = string, authorized_roles = list(string) })",
                    value=f"module.{target}.fis_cluster",
                    description="Native EKS cluster with ready experiment access entries",
                ),
                ModuleInput(
                    module=source,
                    name="fis_eks_pods",
                    type="object({ namespace = string, deployment_name = string, selection_mode = string, service_account = string, kubernetes_group = string })",
                    value=self._renderer.render_expression(settings),
                    description="Explicit pod target and generated Kubernetes access identity",
                ),
                ModuleInput(
                    module=target,
                    name="fis_experiment_roles",
                    type="map(object({ arn = string, native_arn = string }))",
                    value=self._renderer.render_expression(roles),
                    description="Distinct experiment principals resolved without template dependencies",
                ),
            ],
            outputs=[
                self._output(
                    source,
                    "fis_experiment_role",
                    "{ arn = var.role_arn, native_arn = data.aws_iam_role.fis_eks.arn }",
                    "Experiment role identity independent of templates and policies",
                ),
                self._output(
                    source,
                    "eks_pod_access_manifests",
                    'join("\\n---\\n", [for manifest in local.fis_eks_manifests : yamlencode(manifest)])',
                    "Apply these namespace RBAC manifests manually before running experiments",
                ),
                self._output(
                    source,
                    "eks_pod_target",
                    self._renderer.render_expression(
                        {
                            "cluster_arn": Expr("var.fis_eks_cluster.arn"),
                            "cluster_name": Expr("var.fis_eks_cluster.name"),
                            "pods": Expr("var.fis_eks_pods"),
                        }
                    ),
                    "Native cluster and configured pod selector",
                ),
                self._output(
                    target,
                    "fis_cluster",
                    self._renderer.render_expression(
                        {
                            "arn": Expr(f"{cluster}.arn"),
                            "name": Expr(f"{cluster}.name"),
                            "version": Expr(f"{cluster}.version"),
                            "authentication_mode": Expr(
                                f"{cluster}.access_config[0].authentication_mode"
                            ),
                            "authorized_roles": Expr(
                                "[for entry in aws_eks_access_entry.fis_experiments : entry.principal_arn]"
                            ),
                        }
                    ),
                    "Native EKS cluster and ready experiment principals",
                ),
            ],
            resources=[
                self._resource(
                    source, "eks_targets.tf", render_eks_fault_policy(self._renderer)
                ),
                self._resource(source, "eks_pod_manifests.tf", manifests),
                self._resource(
                    source, "FIS-EKS-PODS.md", pod_access_guide(safe_identifier(source))
                ),
                self._resource(
                    target,
                    "fis_access.tf",
                    render_experiment_access(target, self._renderer),
                ),
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        binding = resolve_eks_fault(connection, project)
        return [
            ConnectionIssue(
                severity="warning",
                message=f"This connection creates an EKS pod-delete template for deployment {binding.settings.deployment_name} in namespace {binding.settings.namespace} with {binding.settings.selection_mode}; Terraform does not start experiments. Apply the exported namespace RBAC manifests manually before execution. They use AWS's documented pod, ConfigMap, exec, and ephemeral-container permissions across the namespace; the deployment selector is not an authorization boundary. Shared roles receive the union of applied namespace bindings and IAM permissions. Terraform owns one access entry per distinct experiment role in the cluster; import existing entries before applying. API_AND_CONFIG_MAP is enabled when authentication is unset, and enabling API authentication cannot be reversed. The role must trust fis.amazonaws.com, and deployment requires IAM role lookup/policy/PassRole and EKS access-entry permissions. Native identity guards require the same partition, Region, and account, exact role path, API authentication, and Kubernetes 1.30 or newer. Provision the namespace, Deployment, worker capacity, image access, API networking, and compatible security contexts separately; AWS monitoring requires readOnlyRootFilesystem=false. COUNT resolves at execution and ALL follows live deployment scale. Deletion stops all pod containers, uses their default grace period, and bypasses PodDisruptionBudgets; controllers may replace pods but recovery is not verified. The template preserves source=none stop conditions and overrides standalone action_id. Remove manual RBAC before removing the connection; Terraform destroy does not revoke it. Node-group termination, stress faults, and network faults remain outside this connection.",
            )
        ]
