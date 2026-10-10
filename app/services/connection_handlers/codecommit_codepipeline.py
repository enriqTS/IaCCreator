from app.generators.codecommit_codepipeline import render_pipeline_source_resources
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.codecommit_codepipeline_bindings import (
    resolve_pipeline_source,
)


class CodeCommitPipelineHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        request = resolve_pipeline_source(connection, project)
        target = self._find_instance(connection.target_name, project)
        target.config._repository_source = True
        source = connection.source_name
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=target.name,
                    name="repository_source",
                    type="object({ arn = string, name = string, stage_name = string, action_name = string, branch_name = string })",
                    value=self._renderer.render_expression(
                        {
                            "arn": Expr(f"module.{source}.repository_arn"),
                            "name": Expr(f"module.{source}.repository_name"),
                            **request.model_dump(),
                        }
                    ),
                    description="Native repository and selected existing pipeline source action",
                )
            ],
            outputs=[
                self._output(
                    source,
                    "repository_name",
                    f"aws_codecommit_repository.{source}.repository_name",
                    "Native CodeCommit repository name",
                ),
                self._output(
                    target.name,
                    "repository_source",
                    "var.repository_source",
                    "Connected pipeline repository source settings",
                ),
            ],
            resources=[
                self._resource(
                    target.name,
                    "repository_source.tf",
                    render_pipeline_source_resources(self._renderer),
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_pipeline_source(connection, project)
        return [
            ConnectionIssue(
                severity="warning",
                message="This binds one existing AWS CodeCommit source action to the native repository and selected branch, preserves its ZIP artifact and downstream stages, and grants repository-scoped archive/read permissions to the existing external pipeline role. Polling is disabled; no push rule is created. AWS automatically starts an execution when a pipeline is created, even with polling disabled. Import the existing repository and ensure the branch contains usable content before applying. The role must trust codepipeline.amazonaws.com; deployment needs iam:GetRole, inline-policy management, and iam:PassRole. Artifact-bucket/key access, repository customer-managed key permissions, downstream action grants, and external EventBridge triggers remain separate. CodeCommit stays retired for new placement. Repository permissions cover the entire repository; authorized source revision overrides remain outside the configured branch default.",
            )
        ]
