from app.generators.codecommit_codebuild import render_repository_source_resources
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.codecommit_codebuild_bindings import (
    resolve_repository_source,
)


class CodeCommitBuildHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        request = resolve_repository_source(connection, project)
        target = self._find_instance(connection.target_name, project)
        target.config._repository_source = True
        target.config.source_type = "CODECOMMIT"
        source = connection.source_name
        ref = f"aws_codecommit_repository.{source}"
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=target.name,
                    name="repository_source",
                    type="object({ arn = string, name = string, clone_url = string, source_version = string, git_clone_depth = number })",
                    value=self._renderer.render_expression(
                        {
                            "arn": Expr(f"module.{source}.repository_arn"),
                            "name": Expr(f"module.{source}.repository_name"),
                            "clone_url": Expr(f"module.{source}.clone_url_http"),
                            "source_version": request.source_version,
                            "git_clone_depth": request.git_clone_depth,
                        }
                    ),
                    description="Native primary repository and explicit checkout settings",
                )
            ],
            outputs=[
                self._output(
                    source,
                    "repository_name",
                    f"{ref}.repository_name",
                    "Native CodeCommit repository name",
                ),
                self._output(
                    target.name,
                    "repository_source",
                    "var.repository_source",
                    "Configured primary repository and checkout settings",
                ),
            ],
            resources=[
                self._resource(
                    target.name,
                    "repository_source.tf",
                    render_repository_source_resources(self._renderer),
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_repository_source(connection, project)
        return [
            ConnectionIssue(
                severity="warning",
                message="This configures the native repository as CodeBuild's primary HTTPS source, replacing a NO_SOURCE placeholder. The existing external service role receives repository-scoped codecommit:GitPull and must trust codebuild.amazonaws.com. Terraform verifies the exact role ARN and repository account/Region/partition before policy attachment. The deployment identity needs iam:GetRole, inline-policy management, and iam:PassRole. Import an existing repository before applying; CodeCommit remains retired in the editor catalog. The selected branch/tag/commit and buildspec must exist, with network access and any customer-managed repository-key permissions supplied separately. Submodule fetching, push triggers, artifacts, and build execution are not configured by this edge. Logs and secrets can be connected separately. Authorized StartBuild source/revision/role overrides remain outside these project defaults; GitPull covers the whole repository, not only the selected revision.",
            )
        ]
