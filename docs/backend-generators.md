# Backend Generators

`app/generators/` renders Terraform/HCL from the IR. Every registered service has a dedicated config model and a generator registered in `GENERATOR_REGISTRY`.

## Generator contract and registry

`ServiceGenerator` in `app/generators/base.py` defines `generate_resource_tf`, `generate_variables_tf`, and `generate_outputs_tf`. `GENERATOR_REGISTRY` maps `ServiceType` values to generator instances. Consult that registry as the authoritative list rather than maintaining a duplicate list here.

The registry currently covers core services (including EventBridge), compute, analytics, business applications, databases, developer tools, end-user computing, frontend/web/mobile, games, and machine-learning services. Machine-learning coverage includes Bedrock, SageMaker, Amazon Q, Bedrock Agent, Guardrail, Knowledge Base, and AgentCore. Icon-only `ServiceType` values intentionally have no generator.

API Gateway is split across `app/generators/api_gateway/`: API, routes, integrations, stages, authorizers, domains, VPC links, API keys, and outputs each have focused renderers. `api_gateway_generator.py` remains the registry-facing facade.

## Rendering and schemas

`HCLRenderer` produces Terraform resources, variables, outputs, modules, and providers with two-space indentation. It formats Terraform references rather than quoting them and renders nested values as HCL blocks or collections where appropriate.

Variable schemas are not a hand-maintained `VARIABLE_SCHEMAS` dictionary. Each service's config model uses `TerraformField` metadata; `BaseServiceConfig.get_variable_schema()` derives the schema used by validation, the API endpoint, and the frontend. Metadata includes labels, descriptions, requiredness, defaults, options, validation, groups, and conditional visibility.

`schema_validator.py` validates submitted typed configs against those derived schemas, including closed option sets and conditional fields.

## Project assembly

`FileTreeAssembler` writes environment configuration under:

```
{project}/environments/{environment}/
```

and per-instance modules under:

```
{project}/modules/{category}/{service}/{instance}/
```

Each instance gets its resource, variable, and output files. A service whose config model owns an execution role also gets `iam.tf` and `{project}/iam-policies/{instance}-policy.json`; this is not Lambda-specific.

The assembler uses `module_arguments.py`, `module_paths.py`, and `service_category_map.py` to keep environment module wiring and categorized paths consistent. `TfvarsGenerator` creates environment variable declarations and values; `GlobalConfigGenerator` writes `backend.tf`, `provider.tf`, and `versions.tf`. It emits a default AWS provider plus deterministic Region aliases, and environment module calls select the alias resolved from each resource's semantic Region. An environment `region` variable overrides the default and places all of that environment's modules in the selected Region.

## EC2 launch templates

`ec2-launch-template` generates `aws_launch_template` with an AMI/SSM image reference, instance type, VPC security-group IDs, and optional external key-pair name, base64 user data, and IAM instance-profile name. Template names use provider-generated suffixes and instance metadata requires IMDSv2. Stable outputs expose the template ID, ARN, and latest numeric version. Auto Scaling connections use that numeric version rather than `$Latest`, so template changes appear in the group configuration; rolling replacement of existing instances still requires an explicitly configured refresh policy, which is not introduced by this connection.

Subnet placement belongs to the Auto Scaling group. Managed template connections override its external `launch_template_id` and `launch_template_version` inputs; unconnected groups retain those escape hatches. The frontend exposes the resource through the compute catalog and backend-generated variable schema.

Execution-role policies use `templatefile` with an explicit reference context, so KMS and other ARN expressions resolve before reaching IAM. Cross-module policy resources are exported and passed as module inputs rather than referenced inside a foreign module. Repeated grants are deduplicated before policy rendering.

## Connection-generated Terraform

Connection handlers return `ConnectionContribution`: module inputs, module outputs, module-owned resources, and IAM grants. `FileTreeAssembler` folds those into the owning instance module and passes cross-module values through environment module calls. List-valued network inputs remain typed HCL collections; managed Subnet and Security Group connections merge sorted, deduplicated external IDs with module references, including direct EC2 security-group placement. Network Firewall emits one dynamic subnet mapping per selected Subnet, and Client VPN emits network associations for selected Subnets. This keeps connection resources in their owning module and avoids Terraform dependency cycles.

SQS supports an optional native `kms_master_key_id` input for external key IDs, ARNs, or aliases. KMS connections supply a managed key ARN through that same input, overriding the external fallback. The generator emits the encryption argument only when a key is configured.

KMS consumer IAM grants and service policies are covered in [KMS connection integration](backend-kms-connections.md). Shared keys have one policy owner, and pre-creation identities keep policy-ready outputs cycle-free. Lambda log delivery uses its actual connected log group; ECS application-access grants attach the generated role as the task role.

CloudTrail accepts an optional external `kms_key_id` ARN. Managed KMS connections override it with a policy-ready key output. The connection owns `aws_kms_key_policy` in the key module; the KMS generator leaves its inline policy unset so Terraform has one policy owner. Log-reader decrypt grants and the S3 delivery bucket policy remain separate concerns.

ECS secret connections merge native `secrets` entries into `container_definitions`, preserving unrelated settings and external bindings. Managed bindings replace matching environment variables or secret names. A precondition rejects missing containers, and task creation depends on the secret-access policy. Defaults target the ECS node’s container and use `SECRET_<SECRET_NODE_NAME>` as the environment name. Secrets Manager nodes provision secret metadata; secret values must be populated separately before workloads use them.

EC2 secret connections attach the connection-owned instance profile and make instance creation depend on the secret-access policy. Unconnected instances create no secret role or profile. IAM role and profile names use provider-generated suffixes to avoid account-level naming collisions between generated environments.

CodeBuild emits the required environment and artifact blocks, defaulting to a Linux standard build image, small compute, no artifacts, and a no-source placeholder buildspec. Image, compute type, and buildspec are configurable; the service-role ARN remains an external input. Secret connections add dynamic `SECRETS_MANAGER` environment variables and a project dependency on the inline access policy. The generated project never fetches plaintext secrets. Replace the placeholder buildspec with application build commands before deployment.

App Runner image services expose repository type, optional ECR image-pull role, runtime instance role, and an external secret-ARN map. Private ECR deployments need an access role trusting `build.apprunner.amazonaws.com`; public ECR images disable unsupported automatic deployments. Native secret connections merge environment bindings and make service creation wait for the runtime secret policy. Image-pull authentication and runtime API access remain distinct. Source-code repository injection is not modeled by the current image-only generator.

MWAA secret-read connections make environment creation depend on a consumer-owned inline IAM policy attached to its external execution role. Unconnected environments emit no secret policy or dependency. The generator leaves Airflow configuration and DAG source code untouched; values are fetched at DAG runtime, not by Terraform.

Step Functions secret connections merge SDK task definitions into `jsondecode(var.definition)` and render the result with `jsonencode`. The original workflow remains a configurable input; Terraform preconditions recheck selected placeholders when a generated environment overrides that input. Connections preserve existing JSONPath data paths and transitions while replacing the selected Pass state's dummy Result. Task creation waits for the workflow-owned runtime-access policy. Unconnected state machines continue to use `var.definition` unchanged.
