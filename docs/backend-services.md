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

The current registry includes API Gateway route-handler and authorizer connections; Lambda, ECS, S3, DynamoDB, SNS, and SQS wiring; DynamoDB streams; EventBridge targets; foundational VPC membership and routing; and workload network placement. Internet, NAT, and transit gateways contribute typed destination routes owned by Route Table modules, while managed gateway IDs cross module boundaries through outputs and inputs. Reusable placement handlers aggregate Subnet and Security Group module references by sorted source name, so multiple connections produce one deterministic list input without merge collisions. Supported list-valued targets include Lambda, EKS, EC2 Auto Scaling, Load Balancer, EFS, MemoryDB, DMS, MQ, MWAA, Network Firewall, and Client VPN.

`ConnectionPreviewer` invokes the same handler behavior to return generated resources, IAM grants, and handler-reported issues for the editor. Same-Region policies reject invalid generation, while containment resolution reports a typed `cross-region-connection` issue; explicitly cross-Region IAM and delivery relationships are marked in the registry.

## File assembly

`FileTreeAssembler` writes environment Terraform and categorized, per-instance service modules. It adds connection resources only to the module that owns them and extends recipient module variable/output files for cross-module wiring. Execution roles and policy documents are generated for any service config that declares ownership, rather than being special-cased to Lambda.

## Other services

- `ArchitectureImporter` converts typed generation architectures into deterministic canvas objects, infers registered containment, and normalizes the result before returning it.
- `containment_catalog.py` defines deployment scopes and typed architecture boundaries, including Organizations, organizational units, and accounts, for dynamic editor discovery.
- `ContainmentResolver` returns project-default and per-environment effective scope views; environment `region` and `availability_zone` variables override display scope without copying canonical resources.
- `SessionManager` creates, resolves, and touches anonymous-session users through `AbstractRepository`.
- `diagram_migrations.py` upgrades persisted diagram state on read.
- `services/openapi/` parses an OpenAPI document and maps it to API Gateway configuration for `/api/import/openapi`.

KMS → SQS uses the shared `encrypts` handler and the typed empty connection config. The queue module receives the key module’s `key_arn` output as `kms_master_key_id`; repeated identical connections share one input. This native encryption reference creates no execution role or key-policy back-reference. KMS permissions for queue producers and consumers remain pending shared IAM integration.

KMS → CloudTrail aggregates connected trail identities into one key-owned policy with scoped GenerateDataKey and DescribeKey permissions and the default account administrator statement. Each trail exports an ARN derived from its provider identity and configured name, independently of trail creation. The key module exports the policy resource’s key ARN, so trail creation waits for permissions without a dependency cycle. Repeated connectors are deduplicated; multiple keys for one trail are rejected.

Lambda → Secrets Manager (`reads_secret`) grants runtime GetSecretValue access; application code still retrieves the value. ECS → Secrets Manager (`injects_secret`) injects the secret through the task execution role, with typed container and environment-variable selection. Both aggregate one consumer-owned inline policy using Terraform expressions and grant scoped KMS decrypt access for managed or externally configured encryption keys. External key IDs and aliases resolve through an AWS KMS data source. No secret-version data source retrieves plaintext into Terraform.

EC2 → Secrets Manager (`reads_secret`) reuses the runtime access policy collaborator and creates one EC2-trusted IAM role and instance profile per consumer. Multiple secret connections share those credentials. Managed encryption keys and external key aliases receive scoped decrypt permissions through the same secret-access logic. Application code performs runtime retrieval using instance credentials.

CodeBuild → Secrets Manager (`injects_secret`) creates native secret environment bindings and one consumer-owned inline policy on the configured external service role. The role ARN is required; its trust policy must allow CodeBuild, and build/source/logging permissions remain the external role owner's responsibility. Role paths are supported. Bindings default to `SECRET_<SECRET_NODE_NAME>`; conflicting environment names and reserved `CODEBUILD_` names are rejected. Multiple secrets aggregate deterministically, and the shared runtime-access collaborator supplies scoped GetSecretValue and KMS decrypt permissions without reading secret values into Terraform.

App Runner → Secrets Manager (`injects_secret`) uses the same environment-binding collaborator as CodeBuild. For image-based services it merges managed bindings into `runtime_environment_secrets`, overriding matching external names and preserving unrelated entries. A configured external `instance_role_arn` is required and must trust `tasks.apprunner.amazonaws.com`; secret/KMS permissions attach only to that runtime role, never the ECR `access_role_arn`. External secret bindings retain externally managed permissions. `PORT` and `AWSAPPRUNNER`-prefixed binding names are rejected. Secret values must exist before deployment; rotation requires redeploying the service to refresh injected values.
