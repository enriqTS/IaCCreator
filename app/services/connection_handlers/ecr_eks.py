from app.generators.ecr_eks import render_eks_image_resources
from app.generators.ecr_eks_manifests import image_patch_guide
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier
from app.services.connection_handlers.ecr_eks_bindings import resolve_eks_images


class EcrEksHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        bindings = resolve_eks_images(connection.target_name, project)
        target = connection.target_name
        images = {
            binding.key: {
                **binding.settings.model_dump(),
                "arn": Expr(f"module.{binding.repository}.repository_arn"),
                "url": Expr(f"module.{binding.repository}.repository_url"),
                "name": Expr(f"module.{binding.repository}.repository_name"),
            }
            for binding in bindings
        }
        dependencies = [
            f"aws_eks_cluster.{target}",
            "aws_iam_role_policy.registry_images",
        ]
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=target,
                    name="registry_images",
                    type="map(object({ arn = string, url = string, name = string, image_version = string, namespace = string, deployment_name = string, container_name = string, pull_role_arn = string, pull_role_type = string }))",
                    value=self._renderer.render_expression(images),
                    description="Native images, existing Deployment containers, and external compute pull roles",
                )
            ],
            outputs=[
                *[
                    self._output(
                        repository,
                        "repository_name",
                        f"aws_ecr_repository.{repository}.name",
                        "Native ECR repository name",
                    )
                    for repository in sorted(
                        {binding.repository for binding in bindings}
                    )
                ],
                *[
                    ModuleOutput(
                        module=target,
                        name=name,
                        value=value,
                        description=description,
                        depends_on=dependencies,
                    )
                    for name, value, description in [
                        (
                            "ecr_image_bindings",
                            "local.registry_image_bindings",
                            "Effective repository images and external worker-role bindings",
                        ),
                        (
                            "ecr_image_patches",
                            "{ for workload, patch in local.registry_image_patches : workload => yamlencode(patch) }",
                            "Partial strategic merge patches for existing Deployments; apply manually with kubectl patch",
                        ),
                        (
                            "ecr_image_target",
                            f"{{ arn = aws_eks_cluster.{target}.arn, name = aws_eks_cluster.{target}.name, endpoint = aws_eks_cluster.{target}.endpoint }}",
                            "Native cluster identity to verify before applying image patches",
                        ),
                    ]
                ],
            ],
            resources=[
                self._resource(
                    target,
                    "registry_images.tf",
                    render_eks_image_resources(self._renderer, target),
                ),
                self._resource(
                    target, "ECR-IMAGES.md", image_patch_guide(safe_identifier(target))
                ),
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_eks_images(connection.target_name, project)
        return [
            ConnectionIssue(
                severity="warning",
                message="Use the existing EC2 node or Fargate pod execution role already serving this workload. Pull policies cover all users of that role and preserve its existing permissions. Terraform exports partial Deployment image patches; verify cluster/container identities and apply them manually with kubectl patch --type strategic after reviewing a server dry run. An absent container name would add a container. Push compatible images first; no images, tokens, workers, profiles, Kubernetes workloads, or application credentials are created. Existing imagePullPolicy, deployment strategy, compute association, trust conditions, network access, and Kubernetes RBAC remain prerequisites. Applying a changed pod template can roll out pods; an unchanged mutable tag does not force a rollout. Keep workload GitOps/Helm definitions in sync; removing the edge does not undo manual patches.",
            )
        ]
