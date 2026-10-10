from app.generators.codeartifact_codebuild import render_package_source_resources
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.codeartifact_codebuild_bindings import (
    resolve_package_source,
)


class CodeArtifactBuildHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        request = resolve_package_source(connection, project)
        target = self._find_instance(connection.target_name, project)
        target.config._package_login = True
        source = connection.source_name
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=target.name,
                    name="package_source",
                    type="object({ domain_arn = string, domain_name = string, owner = string, repository_arn = string, repository_name = string, tool = string })",
                    value=self._renderer.render_expression(
                        {
                            name: Expr(f"module.{source}.{name}")
                            for name in (
                                "domain_arn",
                                "domain_name",
                                "owner",
                                "repository_arn",
                                "repository_name",
                            )
                        }
                        | {"tool": request.tool}
                    ),
                    description="Native CodeArtifact domain/repository and runtime package manager",
                )
            ],
            outputs=[
                self._output(
                    source,
                    "domain_name",
                    f"aws_codeartifact_domain.{source}.domain",
                    "Native CodeArtifact domain name",
                ),
                self._output(
                    source,
                    "owner",
                    f"aws_codeartifact_domain.{source}.owner",
                    "Native CodeArtifact domain owner",
                ),
                self._output(
                    target.name,
                    "package_source",
                    "var.package_source",
                    "Read-only CodeArtifact package source",
                ),
            ],
            resources=[
                self._resource(
                    target.name,
                    "package_source.tf",
                    render_package_source_resources(self._renderer),
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_package_source(connection, project)
        return [
            ConnectionIssue(
                severity="warning",
                message="This prepends runtime npm/pip login to an inline version 0.2 pre_build phase, preserving existing commands and other buildspec settings. Package reads use the connected repository and domain; publishing is not granted. The token is fetched only inside the build and uses the remaining assumed-role session lifetime. Install commands run before this login; package retrieval must occur after login. The image must provide a compatible AWS CLI and selected package manager, with network access to CodeArtifact and STS. The existing external service role must trust codebuild.amazonaws.com; deployment needs iam:GetRole, inline-policy management, and iam:PassRole. Domain encryption/upstream/external connections and key policies remain separately configured. This edge does not start builds. Authorized StartBuild role/buildspec overrides and user commands that replace client configuration remain outside these project defaults.",
            )
        ]
