# Service Connections Implementation Plan

## Implementation status

Legend: `[x]` implemented, `[-]` partially implemented, `[ ]` not implemented.

Current phase status:

- [-] Phase 1 foundational networking: VPC membership, routes, subnet placement, and direct security-group placement are implemented; EC2 Auto Scaling security groups require the planned launch-template resource type.
- [-] Phase 2 ingress, load balancing, and DNS: Target Group attachment to EC2 Auto Scaling is implemented; listener, direct target, DNS, certificate, WAF, CloudFront, and accelerator wiring remains.
- [ ] Phase 3 encryption and secrets.
- [-] Phase 4 storage and backup: S3-to-Lambda notifications exist, but the relationships listed in this phase remain.
- [-] Phase 5 databases and application access: Lambda/ECS access to DynamoDB and DMS network placement exist; the listed database integrations remain.
- [-] Phase 6 events, workflows, and APIs: initial Lambda, SQS, SNS, DynamoDB Streams, and EventBridge wiring exists; workflow and API expansion remains.
- [ ] Phase 7 identity, certificates, and edge security.
- [-] Phase 8 observability, governance, and security administration: Lambda-to-CloudWatch logging exists; the broader phase remains.
- [ ] Phase 9 CI/CD and container delivery.
- [ ] Phase 10 analytics and streaming.
- [ ] Phase 11 machine learning.
- [-] Phase 12 IoT, media, migration, and advanced networking: foundational Network Firewall and Client VPN placement exists; the listed advanced integrations remain.

## Purpose

This document is the roadmap for adding semantic connections now that the supported AWS service generators are implemented. It focuses on relationships that replace copied IDs and ARNs with Terraform references, create relationship resources, and grant narrowly scoped IAM access.

Connections remain backend-owned. The frontend discovers them through `/api/connection-schemas` and must not contain service compatibility or transformation logic.

## Current state

The generator registry contains 115 Terraform-capable service types, while the connection registry contains 51 connection specifications involving 29 services.

Implemented coverage includes API Gateway Lambda integrations and authorizers; Lambda and ECS IAM access; Lambda log delivery; S3 notifications; DynamoDB streams; EventBridge targets; SNS subscriptions; SQS event sources; VPC membership; subnet and security-group placement including EKS control-plane security groups; route-table associations; managed Internet, NAT, and transit-gateway routes; and Target Group attachment to EC2 Auto Scaling.

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
- [ ] KMS encryption references and grants;
- [x] route and association resources;
- [ ] target attachments;
- [x] event-source mappings;
- [x] notifications and subscriptions;
- [ ] connection-owned service-role creation;
- [ ] DNS aliases and validation records.

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
- [-] EC2 Auto Scaling: subnet placement exists; security groups belong to its external launch template and require the planned launch-template resource type.
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

- [-] A VPC architecture can be assembled without manually copying VPC, subnet, or security-group IDs; EC2 Auto Scaling remains blocked on a managed launch-template resource.
- [x] Public and private routes are represented by typed connections.
- [x] Multiple subnet and security-group connections aggregate correctly.
- [x] Generated networking projects pass Terraform validation.

## Phase 2 — Ingress, load balancing, and DNS

Implement:

- [ ] Load Balancer → Target Group: create listener/default-action wiring.
- [ ] Target Group → EC2: create target attachment.
- [x] Target Group → EC2 Auto Scaling: supply target-group ARNs.
- [ ] Target Group → ECS: configure the ECS service load-balancer block.
- [ ] Target Group → Lambda: create attachment and invoke permission where supported.
- [ ] Route 53 → Load Balancer: create alias records.
- [ ] Route 53 → CloudFront: create alias records.
- [ ] Route 53 → Global Accelerator: create aliases where supported.
- [ ] Certificate Manager → Load Balancer: configure HTTPS listener certificates.
- [ ] Certificate Manager → CloudFront: configure the viewer certificate.
- [ ] WAF → Load Balancer: create a web ACL association.
- [ ] WAF → CloudFront: supply the web ACL ARN.
- [ ] Global Accelerator → Load Balancer: create endpoint-group and endpoint wiring.

Add standalone listener or endpoint-group resource types if connection ownership cannot remain clear with the existing service models.

### Completion criteria

- [ ] A public HTTPS workload can be modeled from DNS through WAF and load balancing to compute.
- [-] Listener, attachment, alias, and association resources have one unambiguous owning module; Auto Scaling attachment ownership is implemented.
- [ ] Certificate and hosted-zone references are Terraform expressions.

## Phase 3 — Encryption and secrets

### KMS

Implement `encrypted_by` connections from KMS to:

- S3
- DynamoDB
- SNS
- SQS
- CloudWatch
- EBS
- EFS
- Backup
- Secrets Manager
- DataZone
- CodeArtifact
- Lambda
- CloudTrail where applicable

Each connection must supply the target key identifier, add consumer IAM grants where needed, and handle key-policy requirements without creating cycles.

### Secrets Manager

Implement `reads_secret` or native secret-injection connections for:

- Lambda
- ECS
- EC2
- App Runner
- Batch
- CodeBuild
- Step Functions
- MWAA

Do not treat an IAM grant as runtime secret injection when the target supports a distinct native secrets configuration.

### Completion criteria

- Supported services can use a diagram-owned key or secret without copied ARNs.
- IAM access is scoped to the connected resource.
- Multiple secret connections aggregate without policy or variable collisions.

## Phase 4 — Storage and backup

### S3 relationships

Implement:

- S3 → SNS notifications.
- S3 → SQS notifications.
- S3 → EventBridge delivery.
- S3 → S3 replication.
- CloudTrail → S3 delivery.
- AWS Config → S3 delivery.
- MWAA → S3 source bucket.
- Athena → S3 result or data location.
- Kinesis Firehose → S3 destination.
- DataSync ↔ S3 locations after location resources exist.
- Lake Formation → S3 resource registration.
- CloudFront → S3 origin.
- CodePipeline → S3 artifact store.
- Comprehend → S3 training data.

Connection-owned notifications and replication should supersede duplicate configuration-driven generation while preserving external-resource escape hatches.

### EFS, EBS, and Backup

Implement:

- EFS → Subnet mount targets.
- EFS → Security Group.
- EFS → Lambda filesystem configuration.
- EFS → EC2, ECS, and EKS mounts where target models support them.
- EBS → EC2 volume attachment.
- Backup → EBS, EFS, RDS, Aurora, and DynamoDB selections.

### Completion criteria

- Notification, replication, mount, attachment, and backup resources are connection-owned.
- Duplicate converging storage connections aggregate safely.
- Existing raw identifier fields remain usable for external resources.

## Phase 5 — Databases and application access

Expand IAM and runtime access from execution-role-owning services to:

- RDS
- Aurora
- DocumentDB
- Neptune
- ElastiCache
- MemoryDB
- Keyspaces
- Timestream
- OpenSearch
- Kinesis
- MSK
- MQ

Separate these concerns explicitly:

- IAM authorization;
- network reachability;
- runtime endpoint exposure;
- credential ownership.

A connection must not silently create or expose database credentials.

Add DMS connections for:

- DMS → source database.
- DMS → target database.
- DMS → Subnet.
- DMS → Security Group.

Source and target endpoint configurations must be typed and engine-aware. Secrets should be referenced through Secrets Manager rather than embedded where the provider supports it.

### Completion criteria

- Application access grants are resource-scoped.
- Network placement remains separate from logical data access.
- A DMS task can reference managed source and target resources through Terraform expressions.

## Phase 6 — Events, workflows, and APIs

### EventBridge

Add targets for:

- Step Functions
- SNS
- Kinesis
- API Gateway
- ECS
- Batch
- CodeBuild
- Systems Manager documents

Each target handler must own its target resource and create the required invoke role or resource policy.

### SNS, SQS, and dead-letter relationships

Implement:

- SNS → Kinesis Firehose.
- SQS → ECS polling access.
- SQS → SQS dead-letter queue.
- Lambda → SQS dead-letter queue.
- Lambda → SNS dead-letter topic.

Add redrive configuration and queue-policy contributions where required.

### Step Functions

Implement:

- API Gateway → Step Functions.
- EventBridge → Step Functions.
- Step Functions → Lambda.
- Step Functions → ECS.
- Step Functions → Batch.
- Step Functions → SNS.
- Step Functions → SQS.
- Step Functions → DynamoDB.
- Step Functions → EventBridge.

A Step Functions connection must mutate or contribute a state-machine state and grant the corresponding IAM access; permission alone is insufficient.

### AppSync

Implement:

- AppSync → Lambda.
- AppSync → DynamoDB.
- AppSync → OpenSearch.
- AppSync → EventBridge.
- AppSync → RDS or Aurora where supported.
- Cognito → AppSync authentication.

AppSync owns generated data sources and resolver resources.

### Completion criteria

- Every supported EventBridge target has target-specific validation and IAM behavior.
- Workflow connections produce executable state definitions.
- AppSync data-source connections create resolvers or explicitly identify the remaining resolver configuration required.

## Phase 7 — Identity, certificates, and edge security

Implement:

- Cognito → API Gateway: configure a JWT authorizer.
- Cognito → AppSync: configure user-pool authentication.
- Cognito → Load Balancer: configure listener authentication where modeled.
- Private CA → Certificate Manager: issue a private certificate.
- Certificate Manager → Client VPN: supply server and client certificate references.
- Certificate Manager → API Gateway: configure a custom domain certificate.
- Route 53 → Certificate Manager: create DNS validation records.

### Completion criteria

- API and edge authentication can be modeled without copied pool or certificate identifiers.
- ACM DNS validation is generated from a typed relationship.
- Client VPN certificate inputs can be sourced from managed certificate nodes.

## Phase 8 — Observability, governance, and security administration

Implement:

- CloudTrail → S3.
- CloudTrail → CloudWatch.
- AWS Config → S3.
- AWS Config → SNS.
- Managed Grafana → Managed Prometheus.
- Managed Grafana → supported data sources.
- ECS/EKS → Managed Prometheus where a concrete integration is modeled.
- Lambda/ECS/API Gateway → X-Ray.
- Services → CloudWatch log groups where explicit log destinations are supported.
- Fault Injection Simulator → EC2/ECS/EKS targets.
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
- customer gateways;
- Network Firewall policies;
- load-balancer listeners if they cannot remain connection-owned;
- Global Accelerator endpoint groups if they cannot remain connection-owned;
- Direct Connect attachments and associations where needed;
- directory resources for WorkSpaces;
- EC2 launch templates for EC2 Auto Scaling;
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
