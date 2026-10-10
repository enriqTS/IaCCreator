# CodeArtifact package reads in CodeBuild

CodeArtifact → CodeBuild (`reads_packages`) supplies the connected domain/repository to the build and prepends runtime package-manager login to its inline buildspec. `CodeArtifactBuildConfig.tool` selects `npm` (default) or `pip`. This connection grants read-only package access; package publication and other package managers are not modeled.

## Runtime login and buildspec ownership

The build must use a finite JSON-compatible inline YAML buildspec with version `0.2`. File paths, version `0.1`, non-object phases/pre_build, and non-string pre-build command lists are rejected. An absent `phases` or `pre_build` object is created. To connect a project currently using `buildspec.yml`, copy its buildspec content into the inline configuration first; the generator cannot edit a file held in an external source repository.

The emitted buildspec uses Terraform `yamldecode`/`yamlencode` to preserve the original settings and prepend one command to `phases.pre_build.commands`:

```text
aws codeartifact login --tool npm --domain <native-domain> --domain-owner <native-owner> --repository <native-repository> --region <build-region> --duration-seconds 0
```

The tool changes to `pip` when selected. Existing pre-build commands retain their order after login. Install/build/post-build phases, phase options and finally commands, environment settings, reports, cache, and buildspec artifact declarations are preserved. The CodeBuild resource's artifact configuration remains separately owned; a buildspec artifact declaration alone does not change `NO_ARTIFACTS` into an S3 or pipeline artifact store.

Login obtains a token inside the build using its service-role credentials and configures the package manager's client settings. `--duration-seconds 0` ties the token to the remaining assumed-role session lifetime. No Terraform authorization-token data source, persistent token input/output, source credential, plaintext token environment variable, or login-time AWS request is generated. The build image must supply compatible AWS CLI/package-manager versions and network access to CodeArtifact and STS. Long-running sessions may require a runtime refresh.

Install-phase commands execute before login; place package retrieval in pre-build commands after login or later phases. User commands that subsequently replace package-manager configuration can change the selected repository. Configured phase users and failure behavior remain unchanged and must suit the build's workflow. This edge neither installs package-manager tools nor supplies package content, public registry connections, or build commands.

## References, permissions, and guards

The CodeArtifact module exports its native domain name and owner alongside its existing domain/repository ARN and repository name outputs. A typed `package_source` object carries these references and the selected tool into the build module. The build exports this non-secret metadata. No reverse dependency from the domain or repository to the build is introduced.

The build owns an inline policy attached to its existing external `service_role`:

- `codeartifact:GetAuthorizationToken` is scoped to the native domain ARN.
- `codeartifact:GetRepositoryEndpoint` and `codeartifact:ReadFromRepository` are scoped to the native repository ARN.
- `sts:GetServiceBearerToken` uses its required wildcard resource, constrained by `sts:AWSServiceName = codeartifact.amazonaws.com`.

Package reads cover the repository, including packages resolved through its configured upstreams, rather than a package/version allowlist. No publish, deletion, repository administration, or resource-policy changes are granted. The external role must trust `codebuild.amazonaws.com`. Deployment needs `iam:GetRole`, inline-policy management, and `iam:PassRole`. Permission boundaries, explicit denies, domain encryption/key policies, and upstream/public connections remain separately configured.

Terraform resolves the role by basename and checks its complete ARN, including the path, before policy attachment. Source guards verify native domain/repository identities against the caller's account, partition, and Region, including domain ownership and repository membership. Name validation also prevents module overrides from injecting shell syntax into the login command. Tool and inline-buildspec guards protect manually changed Terraform inputs and environment values. These checks run on the build and its package policy; they do not prove role trust, image compatibility, package availability, or network readiness.

## Composition and validation

One repository owns a build's package login. Identical repeated edges are idempotent; different repositories or tools for the same build fail. A domain/repository can serve several builds, including builds sharing an external role; independent policy prefixes avoid replacing another project's grants. Repository and build must share the effective Region in every environment; a global environment Region override can align differently placed nodes.

The connection composes with native CodeCommit primary-source wiring, CloudWatch logging, runtime secrets, managed domain encryption, and configured upstream names. The build retains all policy dependencies and lifecycle guards. No builds are started or package content downloaded during Terraform generation/validation. Authorized `StartBuild` buildspec/role overrides remain outside these project defaults.

`tests/test_codeartifact_codebuild_connections.py` covers property-based native names/tools, duplicates and sharing, backend conflict/buildspec validation, actual emitted IAM-policy evaluation, generated YAML preservation/login ordering, native identity/input guards, and ten cached-provider validation/dependency-graph projects. API tests verify dynamic schema discovery. Checks make no AWS calls or deployments.

References: [AWS npm packages in CodeBuild](https://docs.aws.amazon.com/codeartifact/latest/ug/using-npm-packages-in-codebuild.html), [AWS Python packages in CodeBuild](https://docs.aws.amazon.com/codeartifact/latest/ug/using-python-packages-in-codebuild.html), [CodeArtifact authentication and token lifetimes](https://docs.aws.amazon.com/codeartifact/latest/ug/tokens-authentication.html), [CodeArtifact IAM resource scopes](https://docs.aws.amazon.com/service-authorization/latest/reference/list_codeartifact.html), [CodeBuild buildspec structure](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html), and [Terraform CodeArtifact domains](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codeartifact_domain).
