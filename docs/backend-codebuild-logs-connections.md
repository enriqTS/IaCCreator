# CodeBuild build logging

`CodeBuild → CloudWatch` (`logs_to`) enables the project's native CloudWatch logging destination. `CodeBuildLogsConfig.stream_prefix` defaults to `build` and accepts 1–128 letters, numbers, underscores, dots, slashes, hashes, or hyphens. Each project selects one group and prefix; repeated connections must agree. Several projects may share a group or external service role. [AWS defines the group and stream-prefix settings](https://docs.aws.amazon.com/codebuild/latest/APIReference/API_CloudWatchLogsConfig.html).

## Ownership and wiring

The CloudWatch module owns the group, retention, tags, storage class, and encryption. Its native ARN, name, class, and key ARN cross into the build module through a typed `build_logs` object. Metadata outputs match those used by Grafana, so shared groups retain one output per field. `build_log_destination` exports the selected native destination and prefix.

`CodeBuildGenerator` adds `logs_config.cloudwatch_logs` with `status = "ENABLED"` after existing environment/source rendering. Secret injection, the buildspec, image, compute settings, and artifact configuration remain intact. The project waits for its build logging policy alongside any runtime-secret policy. The connection creates no additional group, service role, CloudWatch delivery policy, source repository, artifact bucket, or running build. Unconnected projects retain their existing generation and AWS logging defaults. [The provider documents the logging block](https://github.com/hashicorp/terraform-provider-aws/blob/main/website/docs/r/codebuild_project.html.markdown).

## Permissions and identity

The build-owned `build_logs.tf` attaches one inline policy to the configured external `service_role`. `name_prefix` prevents policy collisions between projects sharing a role. The native IAM role data source resolves the basename, and lifecycle guards compare the entire returned ARN, including its path, before policy attachment. Partition/account checks reject foreign roles. The deployment identity needs `iam:GetRole`, inline-policy management, and `iam:PassRole`; trust for `codebuild.amazonaws.com`, permission boundaries, and explicit denies remain external. Shared roles retain the union of all their attached permissions. [AWS describes service-role ownership and trust requirements](https://docs.aws.amazon.com/codebuild/latest/userguide/setting-up-service-role.html).

`logs:CreateLogGroup` is restricted to the exact group ARN. `logs:CreateLogStream` and `logs:PutLogEvents` are restricted to that group's stream names beginning with the selected prefix. Prefix matching also permits longer names sharing the same prefix; it is not a per-project security boundary. No discovery, resource-policy administration, log deletion, or retention permission is added. [The service authorization reference defines group and stream resource scopes](https://docs.aws.amazon.com/service-authorization/latest/reference/list_logs.html).

## Encryption and validation

IAM policy generation uses the group's actual native key ARN. Unencrypted groups add no KMS statements. Encrypted groups add key-scoped Encrypt, Decrypt, ReEncrypt*, and GenerateDataKey* permissions constrained by both regional `kms:ViaService` and the exact group's encryption context. DescribeKey is separately constrained to that key and regional service because metadata operations do not carry an encryption context. Managed keys reuse their existing regional Logs service policy. External key owners must authorize both Logs and the CodeBuild service role. Supply an external key ARN rather than an alias or key ID; a connected managed key supersedes that external setting. Artifact encryption is a separate concern. [AWS documents caller permissions and log-group encryption](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html).

Backend validation rejects malformed/missing service roles, conflicting destinations/prefixes, Delivery-class groups, invalid external key references, and effective Region mismatches, including environment overrides. Terraform checks role identity, native group ARN/partition/Region/account, matching group name, Standard or Infrequent Access class, prefix bounds, and native key partition/Region. These destination checks also run on the inline policy before attachment to reject unsafe module overrides.

Build commands can print secrets into logs. Source access, artifacts, network reachability, and ingestion/storage charges remain operational concerns. This connection configures project defaults; users authorized to override logging or service roles in `StartBuild` can change individual builds. [AWS exposes those per-build overrides](https://docs.aws.amazon.com/codebuild/latest/APIReference/API_StartBuild.html).

## Verification

`tests/test_codebuild_logs_connections.py` covers model validation, property-based prefixes/duplicates, native ownership, exact external-role identity, scope guards, actual emitted IAM JSON evaluation, encryption conditions, and secret-injection preservation. Provider validation and plan graphs cover Standard/Infrequent Access, duplicate edges, shared groups/roles, managed/external keys, regional aliases, and combined EventBridge/Secrets Manager/Grafana wiring. API tests verify dynamic discovery of the prefix field. Tests do not deploy resources or run AWS builds.
