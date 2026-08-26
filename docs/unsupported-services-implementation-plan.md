# Unsupported AWS Services Implementation Plan

## Purpose

This document is the phased roadmap for converting currently decorative AWS catalog objects into production-ready Terraform resources. It records the current inventory, the distinction between unsupported states, implementation priorities, and the completion criteria for each service.

The work must proceed phase by phase. A catalog icon must not be advertised as Terraform-supported until its backend model, generator, tests, and required integration points are complete.

## Current state

The backend defines 143 `ServiceType` values:

- 50 have registered Terraform generators.
- 93 are typed icon-only service types without generators.
- The frontend has another 173 decorative catalog occurrences with `serviceType: null`.

Some catalog entries represent the same concept more than once. Fargate appears under Compute and Containers, while other duplicated concepts have one typed and one null occurrence. Counts therefore describe catalog occurrences unless explicitly described as unique service types.

Support currently flows through these components:

- `app/models/input_models/_general.py` defines `ServiceType` and the config-model registry.
- `app/generators/registry.py` is the authoritative Terraform generator registry.
- `/api/editor-bootstrap` reports `supported` based on generator-registry membership.
- `frontend/src/data/aws-icon-registry.ts` maps catalog icons to service types.
- `frontend/src/components/objects/ObjectItemButton.tsx` disables null and unsupported services.

### Unsupported-state definitions

#### Typed icon-only

A typed icon-only service has a `ServiceType` and can be represented as a typed diagram node, but it has no dedicated config model or Terraform generator. It is reported as unsupported by editor bootstrap and disabled in the object picker.

#### Untyped decorative

An untyped decorative service has `serviceType: null` in the frontend catalog. It cannot become an architecture resource and is purely visual catalog data.

#### Genuinely decorative or non-provisionable

Some catalog entries should remain decorative because they represent a client tool, broad product family, support offering, framework, obsolete product, or concept without sensible Terraform ownership. These must be explicitly classified rather than receiving misleading generators.

## Typed icon-only inventory

There are 93 unique typed icon-only service types. Fargate is shown twice in the frontend catalog.

### Analytics — 12

- Clean Rooms
- Data Exchange
- Data Pipeline
- DataZone
- FinSpace
- Glue DataBrew
- Glue Elastic Views
- Kinesis Data Analytics
- Kinesis Data Streams
- Kinesis Video Streams
- Lake Formation
- QuickSight

### Blockchain — 2

- Managed Blockchain
- Quantum Ledger Database

### Business Applications — 11

- Alexa for Business
- Chime SDK
- Chime Voice Connector
- Chime
- Honeycode
- Pinpoint APIs
- Supply Chain
- Wickr
- WorkDocs SDK
- WorkDocs
- WorkMail

### Cloud Financial Management — 7

- Application Cost Profiler
- Billing Conductor
- Budgets
- Cost and Usage Report
- Cost Explorer
- Reserved Instance Reporting
- Savings Plans

### Compute — 25

- Application Auto Scaling
- Bottlerocket
- Compute Optimizer
- EC2 Auto Scaling
- Elastic Fabric Adapter
- Fargate
- Genomics CLI
- Local Zones
- NICE DCV
- NICE EnginFrame
- Nitro Enclaves
- Outposts family
- Outposts rack
- Outposts servers
- ParallelCluster
- Serverless Application Repository
- SimSpace Weaver
- Thinkbox Deadline
- Thinkbox Frost
- Thinkbox Krakatoa
- Thinkbox Sequoia
- Thinkbox Stoke
- Thinkbox XMesh
- VMware Cloud on AWS
- Wavelength

### Containers — 6 catalog occurrences, 5 additional unique types

- ECS Anywhere
- EKS Anywhere
- EKS Cloud
- EKS Distro
- Fargate, duplicated from Compute
- Red Hat OpenShift Service on AWS

### Customer Enablement — 7

- Activate
- IQ
- Managed Services
- Professional Services
- rePost
- Support
- Training Certification

### Database — 4

- Database Migration Service
- Keyspaces
- MemoryDB for Redis
- RDS on VMware

### Developer Tools — 12

- Application Composer
- Cloud Control API
- Cloud Development Kit
- Cloud9
- CloudShell
- CodeArtifact
- CodeCatalyst
- CodeStar
- Command Line Interface
- Corretto
- Tools and SDKs
- X-Ray

### End User Computing — 2

- WorkLink
- WorkSpaces Family

### Front End Web Mobile — 2

- Device Farm
- Location Service

### Games — 4

- GameKit
- GameSparks
- Lumberyard
- Open 3D Engine

## Untyped decorative inventory

The frontend contains 173 `serviceType: null` catalog occurrences.

### App Integration — 7

- AppFlow
- AppSync
- Console Mobile Application
- Express Workflows
- Managed Workflows for Apache Airflow
- MQ
- Step Functions

### General Icons — 2

- Marketplace Dark
- Marketplace Light

### Internet of Things — 16

- FreeRTOS
- IoT 1-Click
- IoT Analytics
- IoT Button
- IoT Core
- IoT Device Defender
- IoT Device Management
- IoT EduKit
- IoT Events
- IoT ExpressLink
- IoT FleetWise
- IoT Greengrass
- IoT RoboRunner
- IoT SiteWise
- IoT Things Graph
- IoT TwinMaker

### Machine Learning — 35

- Apache MXNet on AWS
- Augmented AI A2I
- CodeGuru
- CodeWhisperer
- Comprehend Medical
- Comprehend
- Deep Learning AMIs
- Deep Learning Containers
- DeepComposer
- DeepLens
- DeepRacer
- DevOps Guru
- Elastic Inference
- Forecast
- Fraud Detector
- HealthLake
- Kendra
- Lex
- Lookout for Equipment
- Lookout for Metrics
- Lookout for Vision
- Monitron
- Neuron
- Omics
- Panorama
- Personalize
- Polly
- Rekognition
- SageMaker Ground Truth
- SageMaker Studio Lab
- TensorFlow on AWS
- Textract
- TorchServe
- Transcribe
- Translate

### Management Governance — 27

- AppConfig
- Application Auto Scaling
- Auto Scaling
- Backint Agent
- Chatbot
- CloudFormation
- CloudTrail
- Config
- Control Tower
- Distro for OpenTelemetry
- Fault Injection Simulator
- Launch Wizard
- License Manager
- Managed Grafana
- Managed Service for Prometheus
- Management Console
- OpsWorks
- Organizations
- Personal Health Dashboard
- Proton
- Resilience Hub
- Resource Explorer
- Service Catalog
- Service Management Connector
- Systems Manager
- Trusted Advisor
- Well Architected Tool

### Media Services — 16

- Elastic Transcoder
- Elemental Appliances & Software
- Elemental Conductor
- Elemental Delta
- Elemental Link
- Elemental Live
- Elemental MediaConnect
- Elemental MediaConvert
- Elemental MediaLive
- Elemental MediaPackage
- Elemental MediaStore
- Elemental MediaTailor
- Elemental Server
- Interactive Video Service
- Kinesis Video Streams
- Nimble Studio

### Migration Transfer — 8

- Application Discovery Service
- Application Migration Service
- DataSync
- Mainframe Modernization
- Migration Evaluator
- Migration Hub
- Server Migration Service
- Transfer Family

### Networking Content Delivery — 17

- App Mesh
- Client VPN
- Cloud Directory
- Cloud Map
- Cloud WAN
- CloudFront
- Direct Connect
- Elastic Load Balancing
- Global Accelerator
- Private 5G
- PrivateLink
- Route 53
- Site-to-Site VPN
- Transit Gateway
- Verified Access
- Virtual Private Cloud
- VPC Lattice

### Quantum Technologies — 1

- Braket

### Robotics — 1

- RoboMaker

### Satellite — 1

- Ground Station

### Security Identity Compliance — 24

- Artifact
- Audit Manager
- Certificate Manager
- Cloud Directory
- CloudHSM
- Cognito
- Detective
- Directory Service
- Firewall Manager
- GuardDuty
- IAM Identity Center
- Inspector
- Key Management Service
- Macie
- Network Firewall
- Private Certificate Authority
- Resource Access Manager
- Secrets Manager
- Security Hub
- Security Lake
- Shield
- Signer
- Verified Permissions
- WAF

### Storage — 17

- Backup
- EFS
- Elastic Block Store
- Elastic Disaster Recovery
- File Cache
- FSx for Lustre
- FSx for NetApp ONTAP
- FSx for OpenZFS
- FSx for WFS
- FSx
- S3 on Outposts
- Simple Storage Service Glacier
- Snowball Edge
- Snowball
- Snowcone
- Snowmobile
- Storage Gateway

### VR AR — 1

- Sumerian

## Phase 1 — Service capability model and catalog audit

Before adding generators, make support status explicit and enforce registry consistency.

### Backend capability model

Replace the implicit generator-membership contract with backend-owned service capabilities. Each catalog service should expose at least:

- `diagram`: may be placed on the canvas.
- `terraform`: produces Terraform.
- `configurable`: has editable infrastructure configuration.
- `connectable`: participates in registered semantic connections.
- `lifecycle`: `active`, `deprecated`, `retired`, or `decorative`.

The backend remains the source of truth. `/api/editor-bootstrap` should return these capabilities, and the frontend should only render them.

### Catalog audit

Add an automated audit that reports or rejects:

- frontend service types absent from the backend enum;
- backend service types absent from the frontend catalog;
- duplicate service mappings and aliases;
- null service types awaiting classification;
- generated services missing config models;
- config models missing generators;
- generated services missing category mappings or icons;
- services marked Terraform-capable without generators;
- retired services presented as newly deployable.

Add consistency tests covering the same invariants. Remove stale documentation, including the frontend registry comment claiming that only six services are supported.

### Classification output

Every current null and icon-only entry must be assigned one of:

1. standalone Terraform resource;
2. capability or mode of another resource;
3. composite architecture concept that must be split into resource objects;
4. decorative but active concept;
5. deprecated or retired service retained only for existing diagrams.

Phase 1 is complete when no catalog entry has an unexplained support state.

### Phase 1 implementation status

Phase 1 was completed with the following contracts:

- `app/services/service_catalog.py` is the backend capability and classification registry for every typed `ServiceType`.
- `/api/editor-bootstrap` exposes `diagram`, `terraform`, `configurable`, and `connectable` capabilities plus lifecycle and classification.
- Typed active icon-only services are placeable diagram objects without being represented as Terraform-capable.
- `serviceType: null` explicitly means a decorative frontend icon with no backend resource semantics.
- Retired and decorative typed entries are not placeable for new diagrams; deprecated entries remain placeable for compatibility.
- `scripts/audit_service_catalog.py` compares frontend and backend types, reports decorative icons and aliases, and fails on catalog drift.
- Cross-layer tests enforce complete backend classification, coherent registry capabilities, and the current explicit decorative inventory.

The initial audit records 143 typed service types, 173 explicit decorative icon occurrences, and one duplicate typed mapping: Fargate under both Compute and Containers. Duplicate and null entries remain visible in audit output so later phases can resolve them deliberately.

## Phase 2 — Foundational services

Prioritize services that unlock common production architectures and later connection work.

### Networking

Implement explicit resource objects rather than one oversized VPC configuration:

- VPC — implemented
- Subnet — implemented
- Security Group — implemented
- Route Table — implemented
- Internet Gateway — implemented
- NAT Gateway — implemented
- Elastic Load Balancing, split into load-balancer and target-group resources — implemented
- Route 53 hosted zones — implemented
- CloudFront distributions — implemented

Where appropriate, later extend the same model with VPC endpoints, network ACLs, peering, and related routing resources. Cross-module references must travel through module inputs and outputs.

### Security

- Key Management Service — implemented
- Secrets Manager — implemented
- Cognito — implemented
- Certificate Manager — implemented
- WAF — implemented

### Storage

- Elastic Block Store — implemented
- EFS — implemented
- Backup — implemented

### Application integration

- Step Functions — implemented
- AppSync — implemented
- Amazon MQ — implemented
- Managed Workflows for Apache Airflow — implemented

Phase 2 should establish reusable networking identifiers and outputs needed by compute, database, storage, and security services.

## Phase 3 — High-value typed icon-only services

Promote the most useful existing typed services:

- EC2 Auto Scaling — implemented
- Application Auto Scaling — implemented
- Database Migration Service
- Keyspaces
- MemoryDB for Redis
- CodeArtifact
- X-Ray
- QuickSight
- Lake Formation
- DataZone
- Kinesis Data Analytics
- WorkSpaces

Resolve service identity before implementation:

- Decide whether `kinesis` and `kinesis-data-streams` are aliases or separate resources.
- Model Fargate as an ECS/EKS execution mode unless a valid standalone Terraform ownership model is established.
- Consolidate duplicate Compute and Containers catalog mappings.
- Split broad family icons such as Outposts and WorkSpaces Family into provisionable resource types where necessary.
- Do not promote hardware, runtime, or deployment-mode icons as standalone Terraform resources without clear ownership.

## Phase 4 — Observability and governance

Implement active, provisionable governance services:

- CloudTrail
- AWS Config
- Systems Manager
- Organizations
- Control Tower where Terraform support is sufficiently complete
- Managed Grafana
- Managed Service for Prometheus
- Fault Injection Simulator

Add useful connections to CloudWatch, S3, SNS, EventBridge, Lambda, and IAM. Resource ownership must follow the connection-contribution rules and must not create cross-module dependency cycles.

## Phase 5 — Domain batches

Implement the remaining useful services in coherent batches. A batch includes models, generators, outputs, IAM behavior, connections, and tests rather than isolated icon activation.

### Machine-learning APIs

- Comprehend and Comprehend Medical
- Textract
- Rekognition
- Transcribe
- Translate
- Personalize
- Kendra
- Lex
- Forecast
- Fraud Detector
- HealthLake

Training frameworks, client environments, and broad branding icons should remain capabilities or decorative entries unless they own Terraform resources.

### Internet of Things

- IoT Core
- IoT Greengrass
- IoT Device Management
- IoT Device Defender
- IoT Events
- IoT SiteWise
- IoT TwinMaker
- IoT Analytics where still supported
- IoT FleetWise

Classify retired products before implementation and do not offer them for new deployment.

### Media

- MediaConnect
- MediaConvert
- MediaLive
- MediaPackage
- MediaStore where still supported
- MediaTailor
- Interactive Video Service
- Kinesis Video Streams

Elemental hardware and legacy product icons should not automatically become Terraform resources.

### Migration and transfer

- DataSync
- Transfer Family
- Application Migration Service
- Mainframe Modernization
- Migration Hub resources where meaningful

### Advanced networking and security

- Transit Gateway
- Direct Connect
- Network Firewall
- GuardDuty
- Security Hub
- Macie
- Inspector
- Firewall Manager
- Private Certificate Authority
- Verified Permissions
- VPC Lattice
- Global Accelerator
- Site-to-Site VPN and Client VPN

## Phase 6 — Decorative and lifecycle cleanup

Explicitly retain non-provisionable concepts as decorative. Likely examples include:

- Command Line Interface, Tools and SDKs, Management Console, and CloudShell;
- training, support, professional services, IQ, Activate, and rePost;
- framework/runtime icons such as Corretto, TensorFlow, MXNet, TorchServe, and deep-learning container branding;
- General Icons and marketplace variants;
- broad family, hardware, location, and client-only concepts without independent Terraform ownership.

Review discontinued or restricted services against current AWS and Terraform provider status before implementation. Existing diagrams must remain renderable, but retired services should not be offered as new deployable resources. Candidates include Honeycode, WorkLink, Cloud9, CodeCommit availability-dependent usage, Data Pipeline, Glue Elastic Views, several Thinkbox products, older Elemental products, and other retired catalog entries.

At the end of this phase, every catalog entry must be intentionally Terraform-supported, intentionally decorative, or intentionally retained for backward compatibility.

## Per-service implementation checklist

Each service is a self-contained unit of work and must leave the repository working.

1. Verify current AWS service lifecycle and Terraform AWS provider support.
2. Decide whether the catalog concept is a resource, capability, alias, or composite.
3. Add or promote its `ServiceType` only when it has stable backend semantics.
4. Add a dedicated `BaseServiceConfig` model using `TerraformField` metadata.
5. Model required fields, defaults, options, conditional visibility, and backend validation.
6. Add a focused `ServiceGenerator`; split complex generators into packages or collaborators.
7. Register the config model and generator.
8. Add the service category and module-path coverage.
9. Add resource initialization, naming rules, and typed defaults.
10. Emit useful outputs for cross-module wiring.
11. Add IAM registry actions and resources where applicable.
12. Add connection config models and handlers only through `ConnectionSpec` registrations.
13. Keep connection-owned resources in the owning module and pass cross-module values through inputs.
14. Regenerate `frontend/src/data/bundled-schemas.ts`; never edit it manually.
15. Update catalog capability metadata and remove duplicate or obsolete mappings.
16. Add model, schema, generator, API, property, connection, and Terraform validation tests as applicable.
17. Run backend formatting, lint, and tests.
18. Run frontend lint, tests, and build when frontend artifacts change.
19. Update README and relevant deep-dive documentation.
20. Commit the completed service or coherent service batch with a one-line conventional commit.

## Test requirements

Each generator should have coverage for:

- typed config coercion and validation;
- Terraform schema metadata and default initialization;
- valid HCL generation and two-space indentation;
- variable declarations and environment module arguments;
- outputs and Terraform references rather than hardcoded cross-resource values;
- optional blocks and mutually dependent fields;
- escaping and serialization properties;
- category and module path placement;
- Terraform validation in generated projects where provider behavior permits it.

Each connection should have coverage for:

- registry resolution and schema exposure;
- contribution preview;
- module inputs and outputs;
- module-owned resources;
- IAM grants;
- duplicate contribution aggregation;
- invalid direction, pair, and configuration handling;
- generated-project Terraform validation.

Catalog-level tests should ensure support capabilities shown by the frontend match backend declarations.

## Initial delivery milestone

The recommended first feature milestone after Phase 1 is:

1. VPC
2. Subnet
3. Security Group
4. Route Table and gateways
5. Application Load Balancer and target groups
6. Route 53
7. CloudFront
8. Certificate Manager
9. Cognito
10. Key Management Service
11. Secrets Manager
12. Step Functions

This milestone removes the most visible architecture gaps and creates the networking and security foundations required by later services.

## Definition of completion

The roadmap is complete when:

- every active, provisionable catalog service selected for support has a typed backend model and tested generator;
- every supported connection is backend-defined and produces valid contributions;
- the frontend derives support and configuration entirely from backend APIs;
- no catalog entry is disabled merely because it was never classified;
- decorative, alias, composite, deprecated, and retired entries are explicitly identified;
- generated projects pass the applicable formatting, lint, unit, property, and Terraform validation checks;
- README support lists and deep-dive documentation match the registries.
