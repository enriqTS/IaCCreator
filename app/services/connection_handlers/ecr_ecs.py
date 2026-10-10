from app.generators.ecr_ecs import render_registry_image_resources
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.ecr_ecs_bindings import resolve_registry_images


class EcrEcsHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        bindings = resolve_registry_images(connection.target_name, project)
        target = self._find_instance(connection.target_name, project)
        target.config._registry_images = True
        target.config.ecs_launch_type = "FARGATE"
        images = {
            binding.container: {
                "arn": Expr(f"module.{binding.repository}.repository_arn"),
                "url": Expr(f"module.{binding.repository}.repository_url"),
                "name": Expr(f"module.{binding.repository}.repository_name"),
                "image_version": binding.image_version,
            }
            for binding in bindings
        }
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=target.name,
                    name="registry_images",
                    type="map(object({ arn = string, url = string, name = string, image_version = string }))",
                    value=self._renderer.render_expression(images),
                    description="Native repositories and selected tags/digests for application containers",
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
                self._output(
                    target.name,
                    "registry_images",
                    "local.registry_images",
                    "Effective managed application image references",
                ),
            ],
            resources=[
                self._resource(
                    target.name,
                    "registry_images.tf",
                    render_registry_image_resources(self._renderer, target.name),
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_registry_images(connection.target_name, project)
        return [
            ConnectionIssue(
                severity="warning",
                message="This replaces the selected application container's image with the connected private ECR repository and explicit tag/digest, preserving other container settings and managed collectors. Repository pull permissions are scoped on the existing generated ECS execution role; GetAuthorizationToken retains its required wildcard. Connect every application container using private ECR. The existing role can also be shared with task credentials by other connections. Push a compatible image before deploying tasks; this edge neither builds nor pushes images and does not verify image existence or scanning results. Applying the Terraform ECS service/task changes can start or replace running tasks. Changing content under an unchanged mutable tag does not change the Terraform image reference or force a rollout. Network access to ECR and its S3 image layers, ECS role passing, and deployment capacity remain required.",
            )
        ]
