# Backend Services

The service layer turns validated requests into a Terraform file tree and owns connection, session, migration, and OpenAPI-import processing.

## Generation flow

```
ArchitectureDescription
  -> IRBuilder.build()
  -> CodeGenerator.generate()
  -> ConnectionProcessor.process_all()
  -> FileTreeAssembler.assemble()
  -> OutputSerializer
```

`IRBuilder` resolves typed resources, validates and normalizes connections, resolves stable endpoint IDs, groups instances by service, and produces `ProjectIR`. Valid connection kinds are derived from `CONNECTION_SPECS`, not a separate compatibility table.

`CodeGenerator` obtains one merged `ConnectionContribution` from `ConnectionProcessor` and passes it to `FileTreeAssembler`. `OutputSerializer` returns JSON or a ZIP; ZIP generation can strip the project prefix for downloads.

## Connections

`app/services/connection_handlers/registry.py` is the single source of truth. Each `ConnectionSpec` defines source and target service types, a connection type, label, default selection, Region policy, config model, and handler. `resolve_spec()` supports exact matches, legacy API Gateway roles, and the default for an unambiguous pair.

Handlers return `ConnectionContribution`, not generated files alone. A contribution can add module inputs, outputs, module-owned HCL resources, and IAM grants. `ConnectionProcessor` merges all contributions, then attaches grants to the instance owning the execution role.

The current registry includes API Gateway route-handler and authorizer connections; Lambda, ECS, S3, DynamoDB, SNS, and SQS wiring; DynamoDB streams; EventBridge targets; foundational VPC membership and routing; and workload network placement. Internet, NAT, and transit gateways contribute typed destination routes owned by Route Table modules, while managed gateway IDs cross module boundaries through outputs and inputs. Reusable placement handlers aggregate Subnet and Security Group module references by sorted source name, so multiple connections produce one deterministic list input without merge collisions. External identifiers are retained and deduplicated alongside managed references, including direct EC2 security-group placement. Supported list-valued targets include Lambda, EKS, EC2 Launch Template, EC2 Auto Scaling, Load Balancer, EFS, MemoryDB, DMS, MQ, MWAA, Network Firewall, and Client VPN.

`ConnectionPreviewer` invokes the same handler behavior to return generated resources, IAM grants, and handler-reported issues for the editor. Same-Region policies reject invalid generation, while containment resolution reports a typed `cross-region-connection` issue; explicitly cross-Region IAM and delivery relationships are marked in the registry.

Security Group → EC2 Launch Template (`associates`) supplies template security groups using the shared placement handler. EC2 Launch Template → EC2 Auto Scaling (`launches`) supplies its ID and concrete latest version through module inputs. Duplicate connections are idempotent; one template may serve multiple groups, but multiple templates for one group are rejected. Subnets remain owned by the Auto Scaling group rather than the reusable launch template. These connections create no IAM grants or relationship resources.

## File assembly

`FileTreeAssembler` writes environment Terraform and categorized, per-instance service modules. It adds connection resources only to the module that owns them and extends recipient module variable/output files for cross-module wiring. Execution roles and policy documents are generated for any service config that declares ownership, rather than being special-cased to Lambda.

## Other services

- `ArchitectureImporter` converts typed generation architectures into deterministic canvas objects, infers registered containment, and normalizes the result before returning it.
- `containment_catalog.py` defines deployment scopes and typed architecture boundaries, including Organizations, organizational units, and accounts, for dynamic editor discovery.
- `ContainmentResolver` returns project-default and per-environment effective scope views; environment `region` and `availability_zone` variables override display scope without copying canonical resources.
- `SessionManager` creates, resolves, and touches anonymous-session users through `AbstractRepository`.
- `diagram_migrations.py` upgrades persisted diagram state on read.
- `services/openapi/` parses an OpenAPI document and maps it to API Gateway configuration for `/api/import/openapi`.

KMS → SQS uses the shared `encrypts` handler and the typed empty connection config. The queue module receives the key module’s `key_arn` output as `kms_master_key_id`; repeated identical connections share one input. Native encryption creates no execution role. Existing producer/consumer relationships now contribute scoped key permissions, and SNS/EventBridge delivery contributes service-principal permissions to one aggregated key-owned policy. With a service policy, the native queue input uses the policy-ready `service_key_arn` output. SNS/EventBridge publishers also aggregate into one queue-owned delivery policy, so one publisher cannot overwrite another's queue permissions. See [KMS connection integration](backend-kms-connections.md) for the full matrix and external-policy requirements.

KMS → CloudTrail aggregates connected trail identities into one key-owned policy with scoped GenerateDataKey and DescribeKey permissions and the default account administrator statement. Each trail exports an ARN derived from its provider identity and configured name, independently of trail creation. CloudTrail shares the same policy owner as Logs encryption and queue-delivery service grants, so mixed-service keys never acquire competing policy resources. The key module exports the policy resource’s key ARN, so trail creation waits for permissions without a dependency cycle. Repeated connectors are deduplicated; multiple keys for one trail are rejected.

Lambda → Secrets Manager (`reads_secret`) grants runtime GetSecretValue access; application code still retrieves the value. ECS → Secrets Manager (`injects_secret`) injects the secret through the task execution role, with typed container and environment-variable selection. Both aggregate one consumer-owned inline policy using Terraform expressions and grant scoped KMS decrypt access for managed or externally configured encryption keys. External key IDs and aliases resolve through an AWS KMS data source. No secret-version data source retrieves plaintext into Terraform.

EC2 → Secrets Manager (`reads_secret`) reuses the runtime access policy collaborator and creates one EC2-trusted IAM role and instance profile per consumer. Multiple secret connections share those credentials. Managed encryption keys and external key aliases receive scoped decrypt permissions through the same secret-access logic. Application code performs runtime retrieval using instance credentials.

CodeBuild → Secrets Manager (`injects_secret`) creates native secret environment bindings and one consumer-owned inline policy on the configured external service role. The role ARN is required; its trust policy must allow CodeBuild, and build/source/logging permissions remain the external role owner's responsibility. Role paths are supported. Bindings default to `SECRET_<SECRET_NODE_NAME>`; conflicting environment names and reserved `CODEBUILD_` names are rejected. Multiple secrets aggregate deterministically, and the shared runtime-access collaborator supplies scoped GetSecretValue and KMS decrypt permissions without reading secret values into Terraform.

App Runner → Secrets Manager (`injects_secret`) uses the same environment-binding collaborator as CodeBuild. For image-based services it merges managed bindings into `runtime_environment_secrets`, overriding matching external names and preserving unrelated entries. A configured external `instance_role_arn` is required and must trust `tasks.apprunner.amazonaws.com`; secret/KMS permissions attach only to that runtime role, never the ECR `access_role_arn`. External secret bindings retain externally managed permissions. `PORT` and `AWSAPPRUNNER`-prefixed binding names are rejected. Secret values must exist before deployment; rotation requires redeploying the service to refresh injected values.

MWAA → Secrets Manager (`reads_secret`) grants scoped GetSecretValue and, when needed, KMS decrypt access on the configured external `execution_role_arn`. It reuses the external-role collaborator shared by CodeBuild and App Runner, including path-qualified role names. The role must already trust MWAA and have the environment's other permissions. DAG code retrieves the value through the AWS SDK using a known secret name or ARN; this relationship neither injects environment variables nor configures Airflow's prefix-based secrets backend. External key aliases resolve without retrieving plaintext into Terraform.

Step Functions → Secrets Manager (`reads_secret`) replaces an existing top-level JSONPath Pass state, selected by `state_name` (default `Pass`), with an AWS SDK GetSecretValue Task. The connection preserves Next/End, data paths, comments, unrelated states, and workflow settings; placeholder Result values are replaced. Multiple secrets may occupy different states, and the same secret may serve several states, but conflicting bindings are rejected. Missing/non-Pass states, invalid transitions, JSONata, and unsupported placeholder transformations are rejected. A configured external `role_arn` must trust `states.amazonaws.com`; one workflow-owned policy grants scoped secret access and KMS decryption. The connection never retrieves plaintext during Terraform generation. The preview warns that task output contains secret material: restrict execution-history access and avoid execution-data logging. Secret values must be populated separately before execution.

Batch Job Definition → Secrets Manager (`injects_secret`) reuses the environment-binding collaborator to populate `container_properties.secrets` for EC2 single-container jobs. `execution_role_arn` must reference a role trusted by `ecs-tasks.amazonaws.com`; the connection's secret/KMS policy attaches to that role, never `job_role_arn`. Managed bindings override matching external secrets and plaintext environment variables, preserving unrelated entries. `AWS_BATCH`-prefixed names and conflicting managed bindings are rejected. External secret bindings retain externally managed permissions. The existing Batch compute-environment node does not accept secret connections, and no queue, compute environment, or job submission is created implicitly.

S3 notifications share one bucket-owned `notifications.tf` resource. Lambda connectors aggregate deterministically and duplicate connectors are idempotent. External Lambda, SNS, and SQS notification settings remain in that same resource when managed connectors are present; permissions for external destinations remain externally owned.

S3 → SNS and S3 → SQS (`notifies`) use the same event/filter config and bucket notification owner as Lambda. Standard destinations in the same Region are required. One destination-owned policy aggregates bucket publishers; SQS additionally merges SNS and EventBridge publishers into its existing delivery policy. A dedicated `s3_notification_arn` output depends on the destination policy, so S3 destination validation waits for permissions without depending on the entire destination module. Multiple identical connectors are idempotent; overlapping managed filters for matching event categories are rejected. External notification destinations are retained, with their permissions and filter compatibility remaining the caller's responsibility.

Encrypted notification destinations require customer-managed KMS keys. Managed keys receive one deduplicated S3 service grant for GenerateDataKey and Decrypt, even when the key serves both SNS and SQS. The grant is limited to that key; destination policies restrict delivery to the connected bucket ARNs. This follows the [AWS notification permission model](https://docs.aws.amazon.com/AmazonS3/latest/userguide/grant-destinations-permissions-to-s3.html). External key policies remain externally owned and produce a preview warning; AWS-managed key aliases are rejected.

S3 → EventBridge (`delivers_to`) enables EventBridge in the shared bucket notification resource and supplies a rule-owned event pattern through a module input. Connected bucket names aggregate deterministically; managed `source` and `detail.bucket.name` replace manually copied selectors while other pattern filters remain. The existing rule requires a JSON object pattern (`{}` matches all connected-bucket events). Custom buses, schedules, and top-level/detail `$or` patterns are rejected for this direct-delivery relationship. EventBridge targets remain separate connections.

EBS → EC2 (`attaches`) creates a volume-owned `aws_volume_attachment`. Typed Linux device names default to `/dev/sdf`; one volume may have only one instance/device binding, and overlapping `/dev/sdX` and `/dev/xvdX` aliases are rejected across volumes. EC2 exports its actual Availability Zone, which overrides the connected volume's configured zone. No runtime IAM policy is needed; the Terraform deployment identity performs attachment. Formatting and mounting remain guest-OS tasks, reported in preview.

EFS → Lambda (`mounts`) owns one non-root access point per function in the filesystem module and supplies its mount-ready ARN to Lambda. Typed settings select the local mount path, EFS directory, POSIX user/group, and read or read/write access. The function receives filesystem-scoped ClientMount/ClientWrite grants plus Lambda's required EC2 network-interface operations. One filesystem binding per function is supported. Mount-target subnets and Lambda VPC placement must exist through external IDs or managed connections; matching VPCs, Availability Zones, and NFS security-group rules remain separate network configuration.

Backup → EBS/EFS/RDS/Aurora/DynamoDB (`backs_up`) creates a plan-owned selection containing the managed resource's exact ARN. Each selection requires a typed external backup service-role ARN; the role owner supplies its AWS Backup trust, source-resource permissions, and any KMS permissions. The connector does not create broad managed-policy attachments or enable account-level backup settings. Duplicate selections are idempotent, while conflicting roles for the same plan/resource pair are rejected.
