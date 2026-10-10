# CodeCommit primary CodeBuild source

CodeCommit → CodeBuild (`builds_from`) configures the connected repository as the build project's primary HTTPS source. It supports existing diagrams and keeps CodeCommit's catalog lifecycle retired and placement disabled. Import an existing repository into its generated Terraform address before applying.

## Checkout settings

`CodeCommitBuildConfig` exposes `source_version` (default `main`) and `git_clone_depth` (default `1`). The revision can be an existing ASCII branch, Git tag, or commit ID, up to 256 characters; invalid ref components, whitespace, revision expressions, and interpolation syntax are rejected. Clone depth accepts integers from zero to 25; zero selects full history. The connection does not create a branch, tag, commit, or initial repository content.

CodeBuild's `source` uses `CODECOMMIT` and the repository's native `clone_url_http`. The project-level `source_version` and clone depth come from the connection. Submodule fetching is disabled and TLS verification stays enabled. The existing `buildspec`, build image, compute settings, and artifacts are preserved. Set `buildspec` to `buildspec.yml` or another source-relative path to execute a repository buildspec; the existing default inline placeholder remains until configured.

An absent or `NO_SOURCE` source type is a placeholder that the connection changes to `CODECOMMIT`. An already configured `CODECOMMIT` source is accepted. Other source types, including pipeline-managed sources, are rejected rather than replaced. Environment overrides must retain `CODECOMMIT` while the connection exists.

One primary repository owns each build's source. Identical duplicate edges are idempotent; different repositories, revisions, or depths for the same project fail. One repository can serve several projects, including projects using the same external role. Repository and build must share the effective Region in every environment; a global environment Region override can align differently placed nodes.

## Permissions and ownership

The repository exports its native name in addition to its existing ARN and clone URL. A typed `repository_source` input carries these references and checkout settings into the build module; the build exports its effective configured source. No repository-to-build reverse reference is generated.

The build owns `aws_iam_role_policy.repository_source`, granting only `codecommit:GitPull` on the connected native repository ARN. This permits checkout of repository contents; it is not restricted to the selected revision. It grants no repository writes or discovery permissions and creates no service role. The configured external role must trust `codebuild.amazonaws.com`. Shared external roles retain the union of their policies.

Terraform checks the role's account and partition, resolves it by name, and verifies its complete ARN including path before policy attachment. Repository guards verify its native name/ARN against the caller, partition, and Region, and check that its native HTTPS URL names that exact repository. Revision/depth and source-type guards also protect manually changed module inputs and environment values. These checks do not prove that a selected revision exists or that repository content builds successfully.

The deployment identity needs `iam:GetRole`, inline-policy management, and `iam:PassRole` for the existing role. Network access, any customer-managed repository KMS permissions/key policy, and buildspec-specific AWS permissions remain external. No plaintext credentials or source-credential resources are introduced.

## Composition and execution

Source wiring composes with build-owned CloudWatch logging and runtime secret injection. The project retains all policy dependencies and both source and logging lifecycle guards. EventBridge can separately launch builds of this project through its existing connection. This source edge alone does not create push triggers, webhooks, artifact storage, pipelines, or execute builds.

Authorized `StartBuild` source, revision, buildspec, and service-role overrides remain outside the generated project defaults. Applying or removing the connection updates project defaults and its inline policy; it does not undo a build that has already executed.

## Verification and references

`tests/test_codecommit_codebuild_connections.py` covers property-based names/revisions/clone depths, shared repositories and roles, duplicate ordering, conflict validation, retired placement, native IAM/repository guards, and standalone behavior. Nine projects pass real provider validation and dependency graphs, including logging/secrets and EventBridge composition. API tests verify dynamic discovery. Checks use local cached providers without calling AWS.

References: [Terraform CodeBuild project](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codebuild_project), [AWS CodeBuild source configuration](https://docs.aws.amazon.com/codebuild/latest/APIReference/API_ProjectSource.html), [AWS project revisions](https://docs.aws.amazon.com/codebuild/latest/APIReference/API_Project.html), [CodeBuild service roles](https://docs.aws.amazon.com/codebuild/latest/userguide/setting-up-service-role.html), and [CodeCommit GitPull authorization](https://docs.aws.amazon.com/service-authorization/latest/reference/list_codecommit.html).
