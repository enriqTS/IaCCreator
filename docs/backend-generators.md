# Backend Generators

Lambda renders `dead_letter_config` for connected destinations without mutating external service configuration; a native ARN precondition excludes FIFO destinations. See [Lambda dead-letter connections](backend-lambda-dead-letter-connections.md).

`sqs_redrive.py` renders standalone queue redrive policies with native FIFO/account/region guards; source references enter the destination module through typed inputs. See [SQS dead-letter connections](backend-sqs-dead-letter-connections.md).

DMS Secrets Manager endpoints render secret/access-role references and TLS checks without reading credential values or generating clear-text connection fields. `dms_secret_engines.py` owns the engine/TLS mapping independently of IAM support; RDS SQL Server Enterprise/Standard use `sqlserver` with `verify-full`. RDS Oracle EE/SE2 and CDB variants use `oracle` with `verify-ca` and an externally imported wallet. Explicit Oracle reader choices render fixed extra connection attributes; arbitrary attribute strings are not accepted.

ElastiCache Serverless has a separate Valkey/Redis generator with native TLS, external user-group attachment, placement inputs, and IAM version guards. See [serverless IAM clients](backend-elasticache-serverless.md).

DMS IAM endpoint connections add dedicated endpoint roles and engine-specific endpoint resources, with database identity references and DMS version guards. Full-load and MySQL/PostgreSQL/SQL Server/Oracle-source CDC task rendering references those endpoints and emits explicit table mappings with optional schema renaming and table prefixes, stopped execution, and DO_NOTHING table preparation. See [DMS relational endpoints](backend-dms-connections.md).

ElastiCache exposes parameter-group, engine-version, and external VPC placement settings. Standalone cache connections add engine/count guards and native endpoint/TLS outputs. Memcached supports opt-in TLS with version, VPC, and node-family guards. See [ElastiCache client connections](backend-elasticache-connections.md).

MQ client connections filter every native broker instance's endpoint list by protocol scheme, preserving active/standby endpoints and passing a typed list into the consumer module. See [ActiveMQ client connections](backend-mq-connections.md).

MSK emits native broker placement from typed instance, subnet, and security-group fields. Topic connections enable IAM/TLS and add version and placement guards. See [MSK topic connections](backend-msk-connections.md).

DocumentDB exposes optional `engine_version`; IAM client connections require explicit `5.0` and add Terraform version guards. ECS can attach its runtime role for identity-based database login without adding policy statements. See [DocumentDB client connections](backend-documentdb-connections.md).

`app/generators/` renders Terraform/HCL from the IR. Every registered service has a dedicated config model and a generator registered in `GENERATOR_REGISTRY`.

Managed Grafana data-source connections add a workspace-owned role reference and policy dependency plus native customer-managed/current-account guards. `grafana_data_sources.py` renders shared role trust and policy resources, flattening conditional statement lists into IAM objects. `grafana_prometheus.py` renders native workspace scope checks and credential-free data-source API payloads for the dedicated Amazon Prometheus plugin. `grafana_cloudwatch.py` renders log-group/class/KMS guards, Logs Insights and conditional decrypt permissions, and regional CloudWatch Logs API payloads. `grafana_timestream.py` renders native database/table guards, scoped queries, and payloads with SQL-quoted database/table defaults and ARN-derived UIDs. Unconnected workspace rendering stays unchanged. `grafana_opensearch.py` renders native domain/endpoint/version guards, metadata and root multi-search permissions, and SigV4 plugin payloads. Connected domains enable explicit request-body indexes and HTTPS; index-scoped runtime clients require a separate domain. `grafana_athena.py` renders native workgroup/result guards, selected-table metadata, scoped S3 result access, and one plugin payload per workgroup/database; dataset and encryption permissions remain external. See [Grafana Prometheus connections](backend-grafana-prometheus-connections.md), [Grafana CloudWatch Logs connections](backend-grafana-cloudwatch-connections.md), [Grafana Timestream connections](backend-grafana-timestream-connections.md), [Grafana OpenSearch connections](backend-grafana-opensearch-connections.md), and [Grafana Athena connections](backend-grafana-athena-connections.md).

`grafana_redshift.py` renders provisioned-cluster Data API grants, separate database/user credential statements, native identity/admin-user guards, and plugin payloads. Connected Redshift clusters use AWS-managed administrator passwords; optional `number_of_nodes` controls cluster capacity. See [Grafana Redshift connections](backend-grafana-redshift-connections.md).

`grafana_xray.py` renders regional trace reads, conditional native Insights permissions, group scope guards, regional data-source settings, and native query defaults. Group filters select queries without constraining IAM authorization. See [Grafana X-Ray connections](backend-grafana-xray-connections.md).

`eks_prometheus.py` renders EKS-owned managed scrapers, native networking/scope guards, a VPC DNS lookup, and AWS default scrape configuration with a typed interval. EKS optionally renders private endpoint access and API authentication; connected Prometheus workspaces include AWS's agentless-collector tag. See [EKS Prometheus connections](backend-eks-prometheus-connections.md).

`ecs_prometheus.py` renders ADOT configuration, a collector sidecar, diagnostic logs, and task guards. The ECS generator composes it after secret injection and EFS mounts, preserving application containers and existing guards. Native workspace bindings configure SigV4 remote writes without a custom image or config-upload step. See [ECS Prometheus connections](backend-ecs-prometheus-connections.md).

## Generator contract and registry

`ServiceGenerator` in `app/generators/base.py` defines `generate_resource_tf`, `generate_variables_tf`, and `generate_outputs_tf`. `GENERATOR_REGISTRY` maps `ServiceType` values to generator instances. Consult that registry as the authoritative list rather than maintaining a duplicate list here.

The registry currently covers core services (including EventBridge), compute, analytics, business applications, databases, developer tools, end-user computing, frontend/web/mobile, games, and machine-learning services. Machine-learning coverage includes Bedrock, SageMaker, Amazon Q, Bedrock Agent, Guardrail, Knowledge Base, and AgentCore. Icon-only `ServiceType` values intentionally have no generator.

API Gateway is split across `app/generators/api_gateway/`: API, routes, integrations, stages, authorizers, domains, VPC links, API keys, and outputs each have focused renderers. `api_gateway_generator.py` remains the registry-facing facade.

The Batch generator can add an optional job queue backed by its compute environment and export its ARN. EventBridge Batch connections create that queue when absent and require an unmanaged compute environment with separately registered EC2 capacity.

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

Managed CloudTrail logging adds native CloudWatch destination arguments and waits for its trail-owned delivery policy. `cloudtrail_logs.py` renders role/policy resources, stream scopes, wildcard normalization, and native destination guards. See [CloudTrail logging connections](backend-cloudtrail-logs-connections.md).

ECS secret connections merge native `secrets` entries into `container_definitions`, preserving unrelated settings and external bindings. Managed bindings replace matching environment variables or secret names. A precondition rejects missing containers, and task creation depends on the secret-access policy. Defaults target the ECS node’s container and use `SECRET_<SECRET_NODE_NAME>` as the environment name. Secrets Manager nodes provision secret metadata; secret values must be populated separately before workloads use them.

EC2 secret connections attach the connection-owned instance profile and make instance creation depend on the secret-access policy. Unconnected instances create no secret role or profile. IAM role and profile names use provider-generated suffixes to avoid account-level naming collisions between generated environments.

CodeBuild emits the required environment and artifact blocks, defaulting to a Linux standard build image, small compute, no artifacts, and a no-source placeholder buildspec. Image, compute type, and buildspec are configurable; the service-role ARN remains an external input. Secret connections add dynamic `SECRETS_MANAGER` environment variables and a project dependency on the inline access policy. The generated project never fetches plaintext secrets. Replace the placeholder buildspec with application build commands before deployment.

App Runner image services expose repository type, optional ECR image-pull role, runtime instance role, and an external secret-ARN map. Private ECR deployments need an access role trusting `build.apprunner.amazonaws.com`; public ECR images disable unsupported automatic deployments. Native secret connections merge environment bindings and make service creation wait for the runtime secret policy. Image-pull authentication and runtime API access remain distinct. Source-code repository injection is not modeled by the current image-only generator.

MWAA secret-read connections make environment creation depend on a consumer-owned inline IAM policy attached to its external execution role. Unconnected environments emit no secret policy or dependency. The generator leaves Airflow configuration and DAG source code untouched; values are fetched at DAG runtime, not by Terraform.

Step Functions secret connections merge SDK task definitions into `jsondecode(var.definition)` and render the result with `jsonencode`. The original workflow remains a configurable input; Terraform preconditions recheck selected placeholders when a generated environment overrides that input. Connections preserve existing JSONPath data paths and transitions while replacing the selected Pass state's dummy Result. Task creation waits for the workflow-owned runtime-access policy. Unconnected state machines continue to use `var.definition` unchanged.

Step Functions EventBridge connections append optimized PutEvents tasks after other connected task types, preserving selected Pass-state transitions and paths. EventBridge modules export a bus ARN from the generated custom bus or a lookup of the default bus; workflow tasks and IAM policies consume this output through module inputs.

AppSync Lambda connections leave the GraphQL API generator focused on API configuration. The AppSync-owned connection handler adds a direct Lambda data source, its API-scoped service role, an invocation policy, and one resolver per selected schema field. Lambda ARNs enter through module inputs.

AppSync DynamoDB connections use the same API-owned data-source pattern, with JavaScript unit resolver code generated per selected item operation and native table name/ARN module inputs. Table key names and optional sort keys come from the DynamoDB config; KMS key references cross the module boundary as inputs.

AppSync OpenSearch connections generate JavaScript unit resolvers for document lookup, simple-query-string search, index, and delete operations. The API module owns the data source and scoped role; the domain ARN and endpoint cross from the OpenSearch module as inputs. See [AppSync OpenSearch connections](backend-appsync-opensearch-connections.md).

AppSync EventBridge connections generate JavaScript unit resolvers that publish one event with explicit source/detail type and a GraphQL input object as detail. The API-owned data source consumes the generated EventBridge module's custom or default bus ARN and waits for its bus-scoped role policy. See [AppSync EventBridge connections](backend-appsync-eventbridge-connections.md).

AppSync Aurora connections enable the Data API on an encrypted Aurora PostgreSQL Serverless v2 cluster, create a writer instance, and export a writer-ready cluster ARN. The AppSync module owns the relational data source and JavaScript row resolvers. A supplied database-user secret ARN grants scoped Data API access without giving AppSync the cluster master secret. See [AppSync Aurora connections](backend-appsync-aurora-connections.md).

Cognito AppSync connections render default or additional user-pool authentication directly on the API. `appsync_authentication.py` renders aggregated provider bindings and controls API-key resources/outputs consistently. Pool/client references and the pool's native Region enter through module inputs. See [Cognito AppSync authentication](backend-cognito-appsync-connections.md).

Cognito HTTP API connections emit API-owned JWT authorizers with pool endpoint/client module inputs. The shared `api_gateway/jwt_routes.py` renderer applies selected route bindings to native API routes and Lambda connection routes, preserving their integrations. See [Cognito API Gateway authorization](backend-cognito-api-gateway-connections.md).

Cognito optionally renders a hosted user-pool domain and exports its prefix. ALB connections create dedicated confidential code-grant clients in the load-balancer module and prepend `authenticate-cognito` to selected HTTPS listeners using native pool/domain/client references. The public client remains independent. See [Cognito ALB authentication](backend-cognito-load-balancer-connections.md).

Private CA uses the required `certificate_authority_configuration` block. `private_ca_activation.py` renders connected root signing, activation, and ACM renewal permissions; the ready issuer ARN includes those dependencies. `private_certificate.py` renders private ACM issuance and native guards, suppressing public validation fields/outputs. See [Private CA certificate connections](backend-private-certificate-connections.md).

Route 53 DNS-validation connections own CNAME records in hosted-zone modules with static canonical-domain map keys. ACM modules own shared issuance waiters, expose ready certificate ARNs, and keep native validation-option outputs independent of issuance. `certificate_dns.py` renders native certificate/zone guards. See [ACM DNS-validation connections](backend-certificate-dns-connections.md).

Client VPN keeps native server and client CA ARN inputs. Managed certificate bindings add endpoint lifecycle preconditions through `client_vpn_certificate.py`, checking the native leaf key and ARN Region. Public ACM source modules own shared issuance waiters; external certificate roles keep their configured values. See [Client VPN certificate connections](backend-client-vpn-certificate-connections.md).

`api_gateway/certificate_domain.py` renders connection-owned Regional domains and API mappings with native certificate Region/account/hostname guards. It consumes typed domain bindings, refers to generated stages, and exposes DNS target/hosted-zone outputs through contributions. Public issuance waiters are shared with Client VPN. See [API custom-domain connections](backend-api-gateway-certificate-connections.md).

`batch-job-definition` emits `aws_batch_job_definition` for EC2 single-container jobs, with typed image, integer vCPU count, memory, command, environment maps, and separate execution/application role references. Container properties use `jsonencode` and resource requirements use string values as required by AWS. Native secret connections make definition creation wait for their access policy. The generator exposes revision-qualified ARN, name, and revision outputs. Job queues, Fargate/EKS properties, scheduling connections, image-pull permissions, and compute-environment management remain separate concerns. The existing `batch` node continues to generate only a compute environment. Execution hosts must run an ECS agent version supporting native Secrets Manager injection; values must exist before jobs start.

The S3 generator defers notification generation to the shared connection aggregator when a `notifies` connector exists. Managed Lambda destinations and external notification settings are emitted together, with one permission dependency per managed function.

S3 SNS/SQS notification blocks consume destination ARNs exported after their resource policies are installed. `ModuleOutput.depends_on` carries such resource-level ordering through assembly. The shared queue policy supports S3 alongside SNS and EventBridge, while SNS owns one aggregated S3/Config delivery policy that preserves account-owner permissions. Key-policy aggregation deduplicates equivalent service grants. No notification policy owns resources in another module, and bucket ARN outputs depend only on the bucket itself, keeping notification and encryption dependencies acyclic.

S3 EventBridge delivery shares `aws_s3_bucket_notification` with direct Lambda/SNS/SQS destinations and external notification settings. EventBridge's existing rule consumes a `jsonencode` module argument containing managed bucket-name references; no IAM role or separate bus is created by the connection.

Connected AWS Config delivery channels add a native `sns_topic_arn` input and ARN/partition/Region preconditions while retaining recorder → channel → enabled-status ordering. The SNS policy checks the topic's actual FIFO/encryption attributes and exports a policy-ready ARN. Config source-account and source-ARN outputs derive only from provider identity data, so the topic policy does not depend on the recorder or channel. See [Config notification connections](backend-aws-config-sns-connections.md).

EC2 exports `availability_zone` for EBS placement. The volume module receives the connected instance ID and zone, then owns the attachment resource. Unconnected EBS volumes retain their configured Availability Zone. Changing the connected instance's zone can require volume replacement; attachment does not format a filesystem or configure guest mounts. Multi-Attach is not modeled.

EFS access-point outputs for Lambda depend on mount targets, so function creation waits for network endpoints. Mount-target iteration uses positional keys rather than computed subnet IDs, allowing Terraform to plan new managed subnets. Existing generated projects with subnet-ID-keyed mount targets need Terraform state moves to the corresponding positional keys before applying this generator change. Subnet ordering should remain stable to avoid changing those resource addresses. External Lambda access-point fields remain usable without a managed mount connection.

Backup selections consume existing volume, filesystem, database, cluster, and table ARN outputs through module inputs. Each selection references its own module's generated backup plan ID, so it cannot select resources belonging to a different plan accidentally. Backup role permissions remain externally owned and are called out in preview.

Athena now emits its native result-configuration block for an external or managed `output_location`. Lake Formation keeps ownership of its existing registration resource while connections replace the resource ARN with a module reference. The reusable S3 location handler derives URIs and prefix ARNs in the backend. Offline service schemas include Athena's result-location and enforcement settings.

Managed S3 replication supersedes the configuration-driven replication resource and keeps external destination settings in the shared source-owned configuration. Each managed destination exports an ARN dependent on its versioning resource. KMS-encrypted source replication requires a replica key and emits native encrypted-object selection criteria. Replica key inputs are distinct per destination/prefix. Replication role trust and S3/KMS authorization are explicit external prerequisites, reported in preview.

Firehose supports external `bucket_arn`, `role_arn`, and `s3_prefix` fields for its native `extended_s3_configuration`. Set `destination` to `extended_s3` when supplying an external S3 destination. Managed S3 connections supply the bucket and destination mode and order stream creation after the delivery policy.

A managed CloudFront S3 origin replaces the custom HTTP origin block with `s3_origin_config` and an Origin Access Control reference. External custom origins retain their existing generation. S3 origin permissions aggregate with audit delivery in `bucket_policy.tf`.

`DataSyncS3LocationGenerator` emits `aws_datasync_location_s3` and a stable `location_arn` output. Managed bucket connections own the access-role policy in the location module and order location creation after it.

CodePipeline renders configured stages/actions as nested dynamic blocks from normalized `stages_json`, and an S3 `artifact_store` with optional KMS encryption. Managed artifact connections order creation after the artifact-role policy. Action-specific configuration and permissions remain caller supplied.

EFS runtime generation uses `ecs_efs.py` to merge native ECS task volumes and container mount points, `eks_efs_manifests.py` to render static PV/PVC and workload bindings, and `templates/efs_bootstrap.sh.tftpl` for EC2 TLS/IAM mounts. EC2 mount changes enable user-data replacement. EKS emits Terraform outputs containing YAML and an `EFS-MOUNTS.md` apply guide. See [EFS runtime connections](backend-efs-connections.md).

RDS/Aurora generators use `database_auth.py` to enable IAM authentication and guard supported engines when a database login connection is present. Master-password management is a separate, explicit service option. IAM resource metadata belongs to the database module and crosses module boundaries as inputs. See [relational database connections](backend-database-connections.md).

Connected Neptune clusters enable native IAM authentication and check engine compatibility with a Terraform postcondition. Explicit `engine_version` settings also receive a precondition to guard environment overrides. Unconnected clusters retain their existing authentication behavior. See [Neptune graph connections](backend-neptune-connections.md).

`memorydb_iam.py` renders checks for TLS, explicit ACL selection, and engine compatibility, along with existing-user/ACL data sources. User postconditions validate IAM mode and membership without retrieving passwords. `MemoryDbGenerator` applies client checks only when connected and preserves unconnected configuration. See [MemoryDB connections](backend-memorydb-connections.md).

Connected OpenSearch domains enforce HTTPS/TLS 1.2 and disable explicit request-body indexes through native advanced options. Endpoint and ARN references remain domain-owned and cross into application modules as inputs. See [OpenSearch connections](backend-opensearch-connections.md) for effects on other clients and Dashboards.
