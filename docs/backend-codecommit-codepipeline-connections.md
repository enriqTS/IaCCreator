# CodeCommit pipeline source actions

CodeCommit → CodePipeline (`sources_from`) binds a native repository to one existing AWS CodeCommit source action. CodeCommit remains retired and unavailable for new placement. Import the existing repository into its generated Terraform address before applying; the connection does not create repository content or branches.

## Source action ownership

`CodeCommitPipelineConfig` exposes `stage_name` and `action_name`, both defaulting to `Source`, and `branch_name`, defaulting to `main`. The stage must be the pipeline's first source stage. The selected action must have category `Source`, owner `AWS`, provider `CodeCommit`, version `1`, no inputs, and exactly one valid output artifact. Its output artifact must have only one producer across the pipeline. Selected action role and Region overrides are unsupported.

Configure at least two stages in the pipeline's `stages_json` before connecting. For example, use a first stage named `Source` with a CodeCommit action named `Source` and an output artifact named `source`; the second stage can be a manual approval or an explicitly configured build/deployment action. The connection preserves action names, run order, artifact names, other source actions, and downstream action configuration. A source action using a different provider is rejected. Full-clone output and additional CodeCommit configuration keys are also rejected.

The selected action's configuration is owned by the connection: `RepositoryName` uses the native repository name; `BranchName` uses the explicit branch; `PollForSourceChanges` is `false`; `OutputArtifactFormat` is `CODE_ZIP`. Existing values for these configuration keys are replaced. The branch accepts literal ASCII Git references up to 256 characters, excluding invalid ref components, whitespace, revision expressions, and interpolation. The named branch must exist; a tag or commit ID is not a substitute for an existing branch.

Each pipeline accepts one repository source binding. Identical repeated connections are idempotent; different repositories, selected actions/stages, or branches for the same pipeline fail. One repository can serve several pipelines, including pipelines sharing an external role, and can separately supply CodeBuild's primary source. Repository and pipeline must share the effective Region in every environment.

## Terraform and permissions

The repository exports its native name. A typed `repository_source` module input carries the native name/ARN and action/branch selectors into the pipeline module. The pipeline exports these source settings. There is no reverse repository dependency or cross-module resource ownership.

The pipeline owns `aws_iam_role_policy.repository_source`, granting `codecommit:CancelUploadArchive`, `codecommit:GetBranch`, `codecommit:GetCommit`, `codecommit:GetRepository`, `codecommit:GetUploadArchiveStatus`, and `codecommit:UploadArchive` on the exact connected repository ARN. The ZIP source grants no GitPull, repository writes, or wildcard repository access. These permissions cover the repository rather than only the configured branch.

The external role must trust `codepipeline.amazonaws.com`. Terraform resolves the role by its basename and verifies the complete ARN, including its path, account, and partition, before attaching the source policy. Native repository guards verify its ARN/name against the caller, partition, and deployment Region. Guards also protect branch, selected stage/action, artifact ownership, source format, and artifact-store presence when Terraform inputs are manually overridden. They do not prove branch existence, repository content, role trust, downstream action readiness, or key-policy access.

The pipeline requires an external artifact bucket or a separate CodePipeline → S3 `stores_artifacts` connection. External bucket/key permissions remain external. With a managed artifact store, both source and artifact policies retain their dependencies and source/role guards; a separately connected KMS key remains supported. Repository customer-managed encryption permissions and key policies remain external. The deployment identity needs `iam:GetRole`, inline-policy management, and `iam:PassRole`.

## Execution behavior

The edge creates no EventBridge rule, webhook, or polling trigger. Polling stays disabled even if the original action enabled it. Supply a separate change-detection rule or start later executions manually. **AWS automatically starts an initial execution when a pipeline is created, even with polling disabled.** Prepare the repository branch, artifact access, and downstream actions before applying. Tests generate and validate Terraform without calling AWS or applying a pipeline.

Authorized pipeline source revision overrides and external triggers remain outside this branch default. Existing unrelated source actions keep their own trigger configuration. Removing a connection removes its source policy and restores ordinary stage configuration; it does not undo completed executions.

## Verification and references

`tests/test_codecommit_codepipeline_connections.py` covers property-based selectors/branches, duplicates, sharing, action and artifact conflicts, native role/repository guards, retired placement, source configuration evaluation, and eight real provider validation/dependency-graph projects. Composition includes managed/encrypted artifacts, shared roles, and a repository also connected to CodeBuild. API tests verify dynamic discovery without frontend connection-specific code.

References: [AWS CodeCommit source action configuration and permissions](https://docs.aws.amazon.com/codepipeline/latest/userguide/action-reference-CodeCommit.html), [AWS pipeline execution triggers](https://docs.aws.amazon.com/codepipeline/latest/userguide/pipelines-about-starting.html), and [Terraform CodePipeline resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codepipeline).
