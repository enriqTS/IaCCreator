# Service Connections Implementation Plan

## Implementation status

Legend: `[x]` implemented, `[-]` partially implemented, `[ ]` not implemented.

Current phase status:

- [x] Phase 1 foundational networking: VPC membership, routes, subnet placement, and security-group placement are implemented, including managed launch templates for EC2 Auto Scaling. Managed placement lists preserve external identifiers.
- [x] Phase 2 ingress, load balancing, and DNS.
- [x] Phase 3 encryption and secrets: KMS references, shared service policies, and scoped grants cover the thirteen registered encryption targets and their existing consumers. Lambda/EC2/MWAA reads, ECS/CodeBuild/App Runner/Batch job-definition native injection, and Step Functions GetSecretValue tasks are implemented.
- [x] Phase 4 storage and backup: S3 relationships, EBS attachments, EFS runtime mounts, and Backup selections are implemented. EKS configures the CSI add-on and exports storage manifests for the user to apply.
- [-] Phase 5 databases and application access: Lambda/ECS access to DynamoDB, Kinesis, named Keyspaces/Timestream tables, Neptune graph queries, OpenSearch document APIs, RDS/Aurora and MemoryDB IAM login, DocumentDB IAM client bindings, MSK topic consumers/producers, ActiveMQ and standalone ElastiCache client endpoint bindings, serverless Valkey/Redis IAM access and placement, and DMS network placement, RDS/Aurora IAM and Secrets Manager endpoints, and stopped full-load and MySQL/PostgreSQL/SQL Server/Oracle-source CDC tasks with explicit table mappings and destination schema/prefix transformations exist. RDS SQL Server Enterprise/Standard secret endpoints support full-load and CDC sources with native LSNs and DMS version guards, plus migration targets. RDS Oracle EE/SE2 secret endpoints (including CDB variants) support full-load sources and migration targets; Oracle sources support native-SCN CDC through LogMiner (non-CDB) or an explicit Binary Reader selection (including CDB/PDB); additional endpoint engines remain.
- [-] Phase 6 events, workflows, and APIs: initial Lambda, SQS, SNS, DynamoDB Streams, and EventBridge wiring plus SQS-to-ECS polling access and SQS/Lambda dead-letter relationships exist; workflow and API expansion remains.
- [x] Phase 7 identity, certificates, and edge security: Cognito authentication, Private CA issuance, Client VPN certificate roles, Regional API Gateway domains, and Route 53 public ACM DNS validation are implemented.
- [-] Phase 8 observability, governance, and security administration: Lambda logging/active X-Ray tracing, HTTP API Gateway access logging, ECS application log delivery, EKS control-plane log selection with a dedicated native-name Standard group, Standard/Express Step Functions execution logging, CodeBuild build logging, FIS explicit EC2 reboot/stop templates, ECS OTLP-to-X-Ray collection and shared native group membership, CloudTrail/Config S3 delivery, CloudTrail CloudWatch delivery with scoped service-role/KMS permissions, AWS Config SNS notifications, Managed Grafana Prometheus/CloudWatch Logs/Timestream/OpenSearch/Athena/Redshift/X-Ray query roles/settings, and EKS/ECS Prometheus collection are implemented; broader integrations remain.
- [ ] Phase 9 CI/CD and container delivery.
- [ ] Phase 10 analytics and streaming.
- [ ] Phase 11 machine learning.
- [-] Phase 12 IoT, media, migration, and advanced networking: foundational Network Firewall and Client VPN placement exists; the listed advanced integrations remain.

## Purpose

This document is the roadmap for adding semantic connections now that the supported AWS service generators are implemented. It focuses on relationships that replace copied IDs and ARNs with Terraform references, create relationship resources, and grant narrowly scoped IAM access.

Connections remain backend-owned. The frontend discovers them through `/api/connection-schemas` and must not contain service compatibility or transformation logic.

## Current state

The generator registry contains 119 Terraform-capable service types, while the connection registry contains 216 connection specifications involving 74 services.

Implemented coverage includes API Gateway Lambda integrations and authorizers; Lambda and ECS IAM access; Lambda log delivery; S3 notifications; DynamoDB streams; EventBridge targets; SNS subscriptions; SQS event sources; VPC membership; subnet and security-group placement including EKS control-plane security groups; route-table associations; managed Internet, NAT, and transit-gateway routes; Target Group attachment to EC2 Auto Scaling; and Security Group → EC2 Launch Template → EC2 Auto Scaling wiring.

Most generated services still do not participate in a registered semantic connection. Cross-resource fields outside the implemented coverage therefore still require users to enter IDs, ARNs, names, or endpoints manually.

## Design rules

Every connection must follow these rules:

1. Register one `ConnectionSpec` in `app/services/connection_handlers/registry.py`; the registry is the compatibility source of truth.
2. Use a typed `BaseConnectionConfig` model and expose its schema through the existing API.
3. Return a `ConnectionContribution` containing module inputs, outputs, owned resources, and IAM grants.
4. Keep relationship resources in the module that owns the relationship.
5. Pass cross-module values through module inputs and outputs; never write directly into another service module.
6. Use Terraform references instead of copying generated identifiers into configuration.
7. Aggregate repeated connections deterministically, especially subnet, security-group, target, route, and policy lists.
8. Preserve manually entered identifiers as escape hatches for external resources where useful, but prefer diagram connections for managed resources.
9. Reject unsupported direction, type, and configuration combinations in the backend.
10. Add registry, schema, preview, contribution, aggregation, IAM, and generated-project validation tests.

## Shared connection infrastructure

Before implementing the domain batches, add reusable handlers or collaborators for recurring contribution patterns:

- [x] scalar module-input references;
- [x] append-to-list module-input references;
- [x] execution-role IAM grants;
- [x] subnet and security-group placement;
- [x] KMS encryption references and grants: native references, scoped runtime grants, and aggregated CloudTrail/CloudWatch/SNS-to-SQS/EventBridge-to-SQS key policies are implemented for the registered relationships; external key-policy ownership and AWS-managed service grants are documented in `docs/backend-kms-connections.md`;
- [x] route and association resources;
- [x] target attachments;
- [x] event-source mappings;
- [x] notifications and subscriptions;
- [-] connection-owned service-role creation: EC2 secret access owns an instance role and profile, and CloudTrail logging owns scoped delivery roles; other service roles remain;
- [x] DNS aliases and validation records: Load Balancer, CloudFront, and Global Accelerator aliases plus shared public ACM DNS-validation records are implemented.

Split connection config models and handlers into focused modules as the registry grows. Do not turn the registry, config module, or a generic handler into a god object.

Generators must expose stable outputs needed by connections, normally IDs, ARNs, names, endpoints, hosted-zone IDs, and execution-role ARNs. Add output coverage before registering a connection that consumes an output.

## Phase 1 — Foundational networking

### VPC membership

Implement:

- [x] VPC → Subnet: supply `vpc_id`.
- [x] VPC → Security Group: supply `vpc_id`.
- [x] VPC → Route Table: supply `vpc_id`.
- [x] VPC → Internet Gateway: supply `vpc_id`.
- [x] VPC → private Route 53 hosted zone: create the VPC association.
- [x] VPC → Target Group: supply `vpc_id`.
- [x] VPC → Network Firewall: supply `vpc_id`.

Use a reusable VPC-reference contribution where ownership semantics are identical.

### Subnets and routes

Implement:

- [x] Subnet → NAT Gateway: supply `subnet_id`.
- [x] Subnet → Route Table: create `aws_route_table_association`.
- [x] Internet Gateway → Route Table: add an internet route.
- [x] NAT Gateway → Route Table: add a NAT route.
- [x] Transit Gateway → Route Table: add a transit-gateway route where applicable.
- [x] Subnet → Network Firewall: append firewall subnet mappings.
- [x] Subnet → Client VPN: create `aws_ec2_client_vpn_network_association`.

Add typed route configuration for destination CIDRs and validate gateway-specific requirements.

### Workload placement

Add subnet and security-group connections for:

- [x] Lambda
- [x] EC2
- [x] EKS
- [x] EC2 Auto Scaling: Subnet → Auto Scaling selects workload subnets; Security Group → EC2 Launch Template aggregates security groups; EC2 Launch Template → Auto Scaling supplies a managed ID and concrete latest version. External launch templates remain supported.
- [x] Load Balancer
- [x] EFS
- [x] MemoryDB
- [x] DMS
- [x] MQ
- [x] MWAA
- [x] Network Firewall
- [x] Client VPN

List-valued contributions must merge multiple connectors without replacing existing external-resource values.

### Completion criteria

- [x] A VPC architecture can be assembled without manually copying VPC, subnet, or security-group IDs, including Auto Scaling through managed launch templates.
- [x] Public and private routes are represented by typed connections.
- [x] Multiple subnet and security-group connections aggregate correctly.
- [x] Generated networking projects pass Terraform validation.

## Phase 2 — Ingress, load balancing, and DNS

Implement:

- [x] Load Balancer → Target Group: create listener/default-action wiring.
- [x] Target Group → EC2: create target attachment.
- [x] Target Group → EC2 Auto Scaling: supply target-group ARNs.
- [x] Target Group → ECS: configure the ECS service load-balancer block.
- [x] Target Group → Lambda: create attachment and invoke permission for Lambda target groups.
- [x] Route 53 → Load Balancer: create alias records.
- [x] Route 53 → CloudFront: create alias records.
- [x] Route 53 → Global Accelerator: create alias records.
- [x] Certificate Manager → Load Balancer: configure HTTPS listener certificates.
- [x] Certificate Manager → CloudFront: configure the viewer certificate.
- [x] WAF → Load Balancer: create a web ACL association.
- [x] WAF → CloudFront: supply the web ACL ARN.
- [x] Global Accelerator → Load Balancer: create listener, endpoint-group, and endpoint wiring.

Add standalone listener or endpoint-group resource types if connection ownership cannot remain clear with the existing service models.

### Completion criteria

- [x] A public HTTPS workload can be modeled from DNS through WAF and load balancing to compute.
- [x] Listener, attachment, alias, and association resources have one unambiguous owning module.
- [x] Certificate and hosted-zone references are Terraform expressions.

## Phase 3 — Encryption and secrets

### KMS

Implement `encrypted_by` connections from KMS to:

- [x] S3
- [x] DynamoDB
- [x] SNS
- [x] SQS: native key reference, scoped producer/consumer grants, and managed-key service policies for SNS/EventBridge delivery.
- [x] CloudWatch
- [x] EBS
- [x] EFS
- [x] Backup
- [x] Secrets Manager
- [x] DataZone
- [x] CodeArtifact
- [x] Lambda
- [x] CloudTrail: native encryption and a key-owned policy scoped to connected trail ARNs.

Each connection supplies the target key identifier, adds consumer IAM grants where needed, and handles key-policy requirements without creating cycles. Shared-key integration is complete for the current thirteen native targets and registered consumers; see `docs/backend-kms-connections.md` for the service matrix, AWS-managed grant requirements, and external-key ownership boundaries.

### Secrets Manager

Implement `reads_secret` or native secret-injection connections for:

- [x] Lambda: scoped runtime read access; application code retrieves the value.
- [x] ECS: native container environment injection through its task execution role.
- [x] EC2: scoped runtime read access through a connection-owned role and instance profile.
- [x] App Runner: native image-service environment injection using a configured external instance role, separate from the ECR image-pull role.
- [x] Batch: standalone EC2 single-container job definitions own native secret injection through an external task execution role. The existing Batch compute-environment node remains separate; Fargate/EKS jobs and scheduling relationships are outside this batch.
- [x] CodeBuild: native environment injection with scoped permissions on a configured external service role.
- [x] Step Functions: replaces a selected top-level JSONPath Pass state with an executable GetSecretValue task and scoped permissions on the external execution role.
- [x] MWAA: scoped DAG runtime GetSecretValue access using the external environment execution role; no automatic Airflow secrets-backend configuration.

Do not treat an IAM grant as runtime secret injection when the target supports a distinct native secrets configuration.

### Completion criteria

- [x] Supported services can use a diagram-owned key or secret without copied ARNs.
- [x] IAM access is scoped to the connected resource.
- [x] Multiple secret connections aggregate without policy or variable collisions.

## Phase 4 — Storage and backup

### S3 relationships

Implement:

- [x] S3 → SNS notifications.
- [x] S3 → SQS notifications.
- [x] S3 → EventBridge delivery.
- [x] S3 → S3 live replication with an explicitly configured external replication role.
- [x] CloudTrail → S3 delivery.
- [x] AWS Config → S3 delivery.
- [x] MWAA → S3 source bucket.
- [x] Athena → S3 result location; query data/catalog relationships remain in Phase 10.
- [x] Kinesis Firehose → S3 destination.
- [x] DataSync S3 locations → S3 buckets; DataSync tasks → source/destination locations.
- [x] Lake Formation → S3 resource registration.
- [x] CloudFront → private S3 origin with Origin Access Control.
- [x] CodePipeline → S3 artifact store with validated stage/action definitions.
- [x] Comprehend → S3 training data.

Connection-owned notifications and replication should supersede duplicate configuration-driven generation while preserving external-resource escape hatches.

### EFS, EBS, and Backup

Implement:

- [x] EFS → Subnet mount targets (canonical connection: Subnet → EFS, implemented in Phase 1).
- [x] EFS → Security Group (canonical connection: Security Group → EFS, implemented in Phase 1).
- [x] EFS → Lambda filesystem configuration.
- [x] EFS → EC2 bootstrap mounts with a shared runtime instance role and explicit helper installation.
- [x] EFS → ECS IAM-authorized task volumes and container mount bindings, including subnet/security-group placement.
- [x] EFS → EKS CSI add-on and static PV/PVC manifests for Linux EC2 workers. Users apply the manifests and attach the exported bindings to their workloads. See [EFS runtime connections](backend-efs-connections.md).
- [x] EBS → EC2 volume attachment.
- [x] Backup → EBS, EFS, RDS, Aurora, and DynamoDB selections using explicitly configured external backup roles.

### Completion criteria

- Notification, replication, mount, attachment, and backup resources are connection-owned.
- Duplicate converging storage connections aggregate safely.
- Existing raw identifier fields remain usable for external resources.

## Phase 5 — Databases and application access

Expand IAM and runtime access from execution-role-owning services to:

- [x] RDS: Lambda/ECS IAM login for MySQL, MariaDB, and PostgreSQL with explicit database-user selection and runtime connection metadata.
- [x] Aurora: Lambda/ECS IAM login for Aurora MySQL/PostgreSQL with cluster-resource-ID scoping. Database users, SQL grants, networking, and cluster instances remain separately managed.
- [x] DocumentDB: Lambda/ECS IAM client bindings for explicit engine 5.0, native endpoint references, exported runtime identity, ECS task-role attachment, and version guards. Database users and grants, administrator credentials, cluster instances, and networking remain separate prerequisites.
- [x] Neptune: Lambda/ECS graph read and read/write/delete access, native IAM authentication, resource-ID-scoped grants, runtime endpoints, and guards for engine 1.2.0.0 or newer. Cluster instances and networking remain separate.
- [x] ElastiCache: Lambda/ECS standalone Redis and Memcached endpoint bindings, native transport-state metadata, Memcached discovery, engine/count guards, and opt-in Memcached TLS with version/VPC/node checks. A separate serverless Valkey/Redis node provides native TLS, Lambda/ECS IAM login, and Subnet/Security Group placement; external IAM users and user groups remain deployment prerequisites. Node-based replication groups remain follow-up work.
- [x] MemoryDB: Lambda/ECS IAM login with exact cluster/user grants, existing-user authentication and ACL-membership checks, native TLS/engine guards, and runtime connection metadata. Users, ACLs, command/key permissions, and networking remain separately managed.
- [x] Keyspaces: Lambda/ECS read/write access to explicitly named existing tables, plus required system-metadata reads and runtime connection metadata.
- [x] Timestream: Lambda/ECS read/write access to explicitly named existing LiveAnalytics tables, with separate endpoint discovery and runtime connection metadata. Table provisioning remains separate.
- [x] OpenSearch: Lambda/ECS document read/search and write/delete access on explicitly named index paths, signed HTTPS client metadata, and native restrictions on explicit indexes in request bodies. Domain policies, fine-grained authorization, aliases, and index provisioning remain external.
- [x] Kinesis: Lambda/ECS `reads_from` and `writes_to` grant stream-scoped SDK access and export runtime stream references. Enhanced fan-out, KCL coordination resources, event-source mappings, and customer-managed stream encryption are separate follow-up work.
- [x] MSK: Lambda/ECS exact-topic reads with named consumer groups and non-idempotent writes, native IAM/TLS, broker placement fields, version/topology guards, and private client metadata. Topic provisioning, networking, cluster policies, transactions, and Lambda event sources remain separate.
- [x] MQ: Lambda/ECS typed ActiveMQ TLS endpoint bindings with protocol selection and active/standby endpoint preservation. Broker users, destination permissions, Secrets Manager delivery, networking, and Lambda event sources remain separate.

Separate these concerns explicitly:

- IAM authorization;
- network reachability;
- runtime endpoint exposure;
- credential ownership.

A connection must not silently create or expose database credentials.

Add DMS connections for:

- [-] DMS → source database: RDS/Aurora IAM and Secrets Manager endpoints implemented, including RDS SQL Server Enterprise/Standard and Oracle EE/SE2 (including CDB) secret endpoints; Oracle LogMiner and modern RDS Binary Reader CDC are implemented, including CDB/PDB sources; additional engines remain.
- [-] DMS → target database: RDS/Aurora IAM and Secrets Manager endpoints implemented, including RDS SQL Server Enterprise/Standard and Oracle EE/SE2 (including CDB) secret endpoints; additional engines remain.
- [x] DMS → Subnet.
- [x] DMS → Security Group.

See [DMS relational endpoints](backend-dms-connections.md) for version, certificate, SQL grant, and CDC prerequisites. Endpoint and task ARNs are exported. Full-load and MySQL/PostgreSQL/SQL Server/Oracle-source CDC tasks resolve managed source/target endpoints and map explicitly selected tables with optional destination schema renaming and table prefixes; PostgreSQL CDC uses Secrets Manager sources with typed slot/plugin settings and native WAL positions; filters and column transformations remain unimplemented.

Source and target endpoint configurations must be typed and engine-aware. Secrets should be referenced through Secrets Manager rather than embedded where the provider supports it.

### Completion criteria

- Application access grants are resource-scoped.
- Network placement remains separate from logical data access.
- [x] A DMS full-load task can reference managed source and target resources through Terraform expressions.

## Phase 6 — Events, workflows, and APIs

### EventBridge

Add targets for:

- [x] Step Functions: native target ARN, dedicated rule-scoped invocation role, validated constant input, and identifier conflict checks.
- [x] SNS: standard-topic targets with dedicated publish roles, scoped managed/external KMS access, and validated input.
- [x] Kinesis: stream-scoped PutRecord roles, optional validated partition-key paths, constant input, and target-setting conflict checks.
- [x] API Gateway: static IAM-authorized HTTP POST routes with stage selection and route-scoped invocation roles.
- [x] ECS: Fargate task targets with native task and network references, cluster-scoped RunTask, and task-role PassRole permissions.
- [x] Batch: unmanaged compute-environment queues submit selected generated EC2 job definitions with queue- and definition-scoped roles.
- [x] CodeBuild: standard builds through project-scoped StartBuild roles and native project ARNs.
- [x] Systems Manager Command documents: Run Command targets for explicit managed EC2 instance IDs, with document- and instance-scoped SendCommand roles.

Each target handler must own its target resource and create the required invoke role or resource policy.

### SNS, SQS, and dead-letter relationships

Implement:

- [x] SNS → Kinesis Firehose: standard-topic subscriptions with stream-scoped delivery roles and optional raw messages.
- [x] SQS → ECS polling access: task-role grants scoped to native queue ARNs, URL/region exports, managed/external key decrypt permissions, and application polling guidance.
- [x] SQS → SQS dead-letter queue: bounded receive counts, one destination per source, FIFO/account/region guards, scoped allow policies for up to ten sources, and cycle-free shared/chained Terraform wiring.
- [x] Lambda → SQS dead-letter queue: native destination binding, scoped execution-role send/KMS permissions, conflict and FIFO checks.
- [x] Lambda → SNS dead-letter topic: native destination binding, scoped execution-role publish/KMS permissions, conflict and FIFO checks.

Add redrive configuration and queue-policy contributions where required.

### Step Functions

Secrets Manager GetSecretValue tasks are implemented in Phase 3 using selected Pass-state replacement. The following service tasks remain.

Implement:

- [x] API Gateway → Step Functions: IAM-authorized HTTP POST routes with native asynchronous StartExecution integration and workflow-scoped invocation roles.
- [x] EventBridge → Step Functions: asynchronous StartExecution targets with scoped invocation roles.
- [x] Step Functions → Lambda: selected JSONPath Pass placeholders become Lambda Task states with scoped InvokeFunction grants on the existing execution role.
- [x] Step Functions → ECS: synchronous Fargate RunTask states with managed network references, scoped RunTask/PassRole grants, and task-monitoring permissions.
- [x] Step Functions → Batch: synchronous SubmitJob states using selected generated queues and job definitions, scoped submission and completion-rule grants, and job monitoring permissions.
- [x] Step Functions → SNS: Publish Task states send input or constant messages to generated standard/FIFO topics with topic-scoped publish, FIFO group/deduplication settings, and scoped KMS grants.
- [x] Step Functions → SQS: SendMessage Task states use generated queue URLs, queue-scoped send permissions, standard/FIFO message settings, and scoped KMS grants.
- [x] Step Functions → DynamoDB: optimized GetItem, PutItem, UpdateItem, and DeleteItem Task states use generated table names and operation-scoped table IAM grants.
- [x] Step Functions → EventBridge: optimized PutEvents Task states target generated custom or default buses, with bus-scoped IAM grants and JSON detail from state input or a constant object.

A Step Functions connection must mutate or contribute a state-machine state and grant the corresponding IAM access; permission alone is insufficient.

### AppSync

Implement:

- [x] AppSync → Lambda: direct Lambda resolvers attach selected GraphQL fields to generated AppSync-owned data sources with API-scoped trust and function-scoped invocation roles.
- [x] AppSync → DynamoDB: AppSync JavaScript GetItem, PutItem, UpdateItem, and DeleteItem resolvers use generated table data sources, table-scoped IAM, and key-scoped KMS grants.
- [x] AppSync → OpenSearch: AppSync JavaScript document lookup, search, index, and delete resolvers use an AppSync-owned domain data source and index/path-scoped HTTP grants.
- [x] AppSync → EventBridge: API-owned EventBridge data sources publish one event per selected GraphQL field with bus-scoped IAM and explicit source/detail type.
- [x] AppSync → Aurora PostgreSQL where supported: Data API-backed row resolvers and an API-owned data source use a least-privilege external database-user secret. Standalone RDS instances and Aurora MySQL are not supported by this connection.
- [x] Cognito → AppSync authentication: default or additional user-pool providers consume managed pool/client references, restrict tokens to the generated client by default, and validate conflicting providers.

AppSync owns generated data sources and resolver resources.

### Completion criteria

- Every supported EventBridge target has target-specific validation and IAM behavior.
- Workflow connections produce executable state definitions.
- AppSync data-source connections create resolvers or explicitly identify the remaining resolver configuration required.

## Phase 7 — Identity, certificates, and edge security

Implement:

- [x] Cognito → API Gateway: API-owned JWT authorizers use native pool endpoints and generated client audiences, bind selected existing HTTP routes, share across routes, and validate scopes/authentication conflicts.
- [x] Cognito → AppSync: default/additional user-pool authentication with native pool Region and client filtering; see Phase 6.
- [x] Cognito → Load Balancer: HTTPS Application Load Balancer listeners authenticate through a managed pool domain and dedicated confidential OAuth client before forwarding, with explicit callback hostnames, isolated sessions, and conflict/Region validation.
- [x] Private CA → Certificate Manager: activate the modeled root CA, grant account-scoped ACM renewal permissions, and issue managed private certificates with native CA references, supported key selection, and conflict/Region validation.
- [x] Certificate Manager → Client VPN: supply managed server and client CA certificate references, validate roles/keys/Regions, and wait for public issuance. Client credentials and profiles remain operational prerequisites.
- [x] Certificate Manager → API Gateway: create Regional TLS 1.2 domains and stage/path mappings with ready managed certificate references, hostname/Region/account guards, deterministic aggregation, and ownership/conflict validation. WebSocket stage deployment and DNS remain explicit prerequisites.
- [x] Route 53 → Certificate Manager: public DNS validation CNAMEs cover primary/SAN names across connected zones, share wildcard/apex and cross-Region certificate records, and feed shared issuance waiters. Typed TTL, native guards, and deterministic zone ownership prevent conflicting records; delegation remains an operational prerequisite.

### Completion criteria

- API and edge authentication can be modeled without copied pool or certificate identifiers.
- ACM DNS validation is generated from a typed relationship.
- Client VPN certificate inputs can be sourced from managed certificate nodes.

## Phase 8 — Observability, governance, and security administration

Implement:

- [x] CloudTrail → S3: managed delivery bucket and aggregated service policy; see Phase 4.
- [x] CloudTrail → CloudWatch: trail-owned delivery role/policy, native destination references, effective Region and native account/partition guards, scoped encrypted-log permissions, and deterministic duplicates/sharing.
- [x] AWS Config → S3: managed delivery bucket and aggregated service policy; see Phase 4.
- [x] AWS Config → SNS: native delivery-channel notifications consume policy-ready standard, unencrypted topics; topic-owned policies aggregate Config and S3 publishers with scoped service permissions, native destination guards, and deterministic duplicates.
- [x] Managed Grafana → Managed Prometheus: workspace-owned customer-managed roles grant native workspace-scoped query access; typed endpoint/Region bindings export credential-free Grafana API payloads for manual application, with deterministic sharing and native scope guards.
- [-] Managed Grafana → supported data sources: CloudWatch log-group queries and selected Timestream table queries share the workspace role with Prometheus. Native scope guards, explicit regional discovery/cancellation permissions, conditional log-key decryption, and credential-free data-source settings are implemented. Timestream requires separately provisioned tables and an eligible LiveAnalytics account. OpenSearch adds native endpoint/version settings and domain-wide root multi-search permissions with a concrete default index; same-domain index-scoped Lambda/ECS/AppSync clients are rejected because their explicit-index settings conflict. Athena adds workgroup-scoped execution, selected Glue-table metadata, enforced S3 result-prefix permissions, and native plugin settings; dataset S3/KMS/Lake Formation grants remain external. Redshift adds provisioned-cluster Data API execution, exact existing database/user credential pairs, native guards/settings, and AWS-managed administrator passwords; SQL grants and database/user provisioning remain external, and statement access is shared across workspace role sessions. X-Ray adds regional trace/graph/group reads, conditional regional Insights access, and native group query defaults; filters do not restrict IAM access, and instrumentation/ingestion remain external. Additional data sources remain.
- [x] EKS/ECS → Managed Prometheus: EKS native managed scrapers use private endpoints, API authentication, cluster networking, AWS default jobs, typed intervals, native guards, and drift-free workspace tagging. AWS owns scraper roles and cluster access. ECS adds one pinned ADOT sidecar per modeled Linux Fargate task, task/container metrics and optional localhost application scraping, native SigV4 destinations, workspace-scoped remote-write grants, capacity/ownership guards, and composition with secrets/EFS. See [EKS Prometheus connections](backend-eks-prometheus-connections.md) and [ECS Prometheus connections](backend-ecs-prometheus-connections.md).
- [-] Lambda/ECS/API Gateway → X-Ray: Lambda active tracing and ECS task-local OTLP collection add regional upload permissions and native producer selectors combined with existing predicates. Shared groups, module guards, Prometheus/EFS/secrets composition, and Grafana query settings remain acyclic. ECS preserves application service names and stamps native cluster annotations; local pinned-collector checks verify exported spans. API Gateway tracing is deferred until REST API generation exists: AWS supports X-Ray only for REST APIs, while this project models HTTP/WebSocket APIs. See [protocol limits](backend-api-gateway-logs-connections.md#protocol-limits). See [Lambda X-Ray connections](backend-lambda-xray-connections.md) and [ECS X-Ray connections](backend-ecs-xray-connections.md).
- [-] Services → CloudWatch log groups where explicit log destinations are supported: Lambda, CloudTrail, selected HTTP API Gateway stages, ECS application containers, EKS control-plane logs, Step Functions execution logs, and CodeBuild build logs are implemented. HTTP stages consume native destinations and typed formats, preserve stage ownership, and use AWS-managed log delivery with deployment-identity permissions; ECS containers add native driver settings, explicit delivery modes/buffer memory guards, existing execution-role attachment, conditional scoped caller key permissions, and composition with secrets/EFS/collectors. EKS selects native log types, derives its dedicated fixed-name group from an input-only cluster output, and waits for the Standard destination without a cycle; customer-managed EKS log encryption requires separate service-linked-role key-policy support. Step Functions configures Standard/Express event levels and opt-in payload inclusion, adds an external-role policy with scoped stream writes and required wildcard delivery-management permissions, and preserves service-task guards/dependencies. Managed log encryption reuses the regional Logs service key policy; state-machine encryption remains separate. CodeBuild adds native group/prefix defaults, exact external-role identity checks, scoped group/stream permissions, and conditional caller key access while preserving secret injection; project logging composes with EventBridge/Grafana. WebSocket account logging and additional service destinations remain. See [HTTP API access logs](backend-api-gateway-logs-connections.md), [ECS application logs](backend-ecs-logs-connections.md), [EKS control-plane logs](backend-eks-logs-connections.md), [workflow execution logs](backend-step-functions-logs-connections.md), and [CodeBuild build logs](backend-codebuild-logs-connections.md).
- [-] Fault Injection Simulator → EC2/ECS/EKS targets: EC2 explicit-instance reboot/stop templates support one to five native instances, COUNT/ALL selection, external-role policies, and native scope/stop-eligibility guards. Terraform creates templates without starting experiments; stop omits automatic restart. ECS/EKS targets remain. See [FIS EC2 targets](backend-fis-ec2-connections.md).
- Systems Manager → EC2 document associations.
- Organizations → GuardDuty, Security Hub, Macie, Inspector, and Firewall Manager delegated administration where provider resources support it.

Account-enablement services should remain standalone when a connector would have no Terraform semantics.

### Completion criteria

- Phase 4 services from the unsupported-services roadmap have useful CloudWatch, S3, SNS, EventBridge, Lambda, and IAM relationships.
- Organization-level connections create concrete administration resources rather than decorative edges.

## Phase 9 — CI/CD and container delivery

Implement:

- CodeCommit → CodeBuild.
- CodeCommit → CodePipeline.
- CodeArtifact → CodeBuild.
- ECR → ECS.
- ECR → EKS.
- ECR → App Runner.
- CodeBuild → ECR.
- CodeBuild → S3.
- CodeBuild → CodePipeline.
- CodeDeploy → ECS.
- CodePipeline → CodeBuild.
- CodePipeline → CodeDeploy.
- CodePipeline → S3.
- CodePipeline → ECR.

CodeCommit is retired for new placement, so its connections exist for compatibility with existing diagrams and must not make it newly placeable.

### Completion criteria

- A container delivery pipeline can reference managed source, build, registry, and deployment resources.
- Pipeline stages and artifact stores have explicit ownership.
- Retired-service lifecycle behavior remains unchanged.

## Phase 10 — Analytics and streaming

Implement:

- Kinesis → Lambda event source.
- Kinesis → Kinesis Firehose.
- Kinesis Firehose → S3.
- Kinesis Firehose → OpenSearch.
- MSK → Lambda event source.
- S3 → Athena.
- S3 → Glue.
- Glue → Lake Formation.
- Lake Formation → S3.
- Lake Formation → Glue catalog resources where modeled.
- Redshift/OpenSearch → QuickSight.
- S3/Athena → QuickSight where a concrete Terraform relationship exists.

Kinesis and MSK Lambda integrations should reuse an event-source-mapping abstraction while retaining source-specific configuration and IAM actions.

### Completion criteria

- Streaming sources can feed supported consumers and destinations.
- Analytics access relationships grant only required permissions.
- Connections without concrete Terraform semantics are not registered.

## Phase 11 — Machine learning

Implement the initial useful set:

- S3 → Comprehend.
- S3 → Rekognition.
- S3 → Transcribe.
- S3 → SageMaker.
- S3 → Kendra.
- Kendra → Amazon Q.
- Bedrock Knowledge Base → Bedrock Agent.
- Bedrock Guardrail → Bedrock Agent.
- Bedrock Knowledge Base → supported vector store.
- Bedrock Agent → Lambda action group.
- KMS → Bedrock, Bedrock Agent, and Bedrock Knowledge Base where supported.
- CloudWatch → Bedrock and SageMaker logging where concrete configuration exists.

Introduce separate vector collection, index, data source, or action-group resource objects if the current product-level nodes cannot own the relationship cleanly.

### Completion criteria

- Bedrock components can form a minimally useful agent architecture.
- Training and indexing services can access managed data sources through scoped IAM grants.
- API-only capability nodes do not gain misleading Terraform connections.

## Phase 12 — IoT, media, migration, and advanced networking

### IoT

Implement:

- IoT Device Management → IoT Core thing-group membership.
- IoT Core → Lambda topic-rule action.
- IoT Core → S3, SNS, SQS, Kinesis, and Firehose topic-rule actions.

IoT Core currently owns a registry thing, so messaging relationships require connection-owned `aws_iot_topic_rule` resources and IAM roles.

### Media

Add only relationships backed by the concrete provisioned resource types, such as IVS monitoring or event delivery. Do not connect product icons when the provider has no owned relationship resource.

### Migration and advanced networking

Implement:

- DataSync → source location.
- DataSync → destination location.
- Transfer Family → S3.
- Transfer Family → EFS.
- Transfer Family → CloudWatch.
- Direct Connect → Transit Gateway.
- Site-to-Site VPN → Transit Gateway.
- Client VPN → Subnet.
- Network Firewall → VPC.
- Network Firewall → Subnet.
- VPC Lattice → VPC and resource associations.
- Global Accelerator → Load Balancer.

### Completion criteria

- IoT actions produce topic rules and scoped roles.
- Migration tasks reference independently owned locations.
- Advanced networking relationships use explicit attachment and association resources.

## Missing resource types

Some desired relationships cannot be modeled cleanly with the current service inventory. Add focused resource types before implementing the corresponding connections:

- DataSync locations;
- ElastiCache node-based replication groups; serverless Valkey/Redis IAM support is implemented;
- Batch job queues for scheduling and submission relationships;
- customer gateways;
- Network Firewall policies;
- load-balancer listeners if they cannot remain connection-owned;
- Global Accelerator endpoint groups if they cannot remain connection-owned;
- Direct Connect attachments and associations where needed;
- directory resources for WorkSpaces;
- Bedrock vector collections, indexes, data sources, and action groups where required.

These must be explicit resources rather than large untyped blobs inside a connection config.

## Per-connection implementation checklist

1. Confirm the AWS and Terraform relationship semantics.
2. Decide direction, connection type, label, default behavior, and owning module.
3. Verify both services expose the necessary stable outputs.
4. Add a typed connection config with validation and frontend metadata.
5. Implement a focused handler or reuse a universal contribution collaborator.
6. Register the `ConnectionSpec`.
7. Add module inputs and outputs for cross-module references.
8. Add relationship resources only to their owning module.
9. Add scoped IAM grants and resource policies.
10. Handle repeated and converging connections deterministically.
11. Preserve external-resource configuration where appropriate.
12. Add schema and registry resolution tests.
13. Add preview and handler contribution tests.
14. Add invalid direction, type, and configuration tests.
15. Add duplicate aggregation and path-collision tests.
16. Add the connection to representative architecture coverage.
17. Run generated-project Terraform validation.
18. Update backend service and generator documentation.
19. Commit the completed connection or coherent connection batch.

## Test requirements

Each connection batch must cover:

- registry resolution and API schema exposure;
- typed defaults, options, and validation;
- connection preview output;
- module inputs and outputs;
- relationship-resource ownership;
- IAM actions and resource scoping;
- multiple connections targeting one module;
- deterministic aggregation and naming;
- invalid direction and unsupported combinations;
- legacy payload compatibility where applicable;
- generated-project Terraform loading and validation.

`tests/test_all_connections_validate.py` derives cases from `CONNECTION_SPECS`; every newly registered connection must work with its minimal architecture fixture. Extend shared fixture builders rather than bypassing registry-derived validation.

## Recommended delivery order

1. VPC, subnet, security-group, and route wiring.
2. Load balancer, target group, compute, and Route 53.
3. ACM, WAF, CloudFront, and Global Accelerator.
4. KMS and Secrets Manager.
5. S3 integrations, EFS, EBS, and Backup.
6. EventBridge, Step Functions, SNS/SQS, and AppSync.
7. Database access and DMS.
8. CloudTrail, Config, Grafana, Prometheus, X-Ray, and organization security.
9. CI/CD and container delivery.
10. Analytics and streaming.
11. Machine learning.
12. IoT, media, migration, and advanced networking.
13. Add missing standalone resource types as dependencies are encountered.

## Definition of completion

Connection implementation is complete when:

- every useful relationship between supported resource types is either registered or explicitly rejected as having no Terraform semantics;
- generated architectures no longer require copied identifiers for resources represented in the same diagram;
- relationship resources have clear module ownership;
- cross-module references use module inputs and outputs without dependency cycles;
- IAM grants and resource policies are narrowly scoped;
- repeated connections aggregate deterministically;
- the frontend derives all compatibility and configuration from backend APIs;
- every registered connection passes preview, aggregation, generated-project, and Terraform validation tests;
- service capability metadata and documentation match the connection registry.
