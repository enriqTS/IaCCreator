# Backend Models

`DmsIamEndpointConfig` requires an endpoint identifier, existing database user/name, and imported DMS CA certificate ARN. See [DMS relational IAM endpoints](backend-dms-connections.md).

ElastiCache `connects_to` uses the typed empty connection config. Service fields select a standalone Redis or Memcached cluster and existing parameter/network resources; see [ElastiCache client connections](backend-elasticache-connections.md).

`MqClientConfig` exposes an AMQP-default TLS protocol selector for the current ActiveMQ node. Connections accept no username, password, or messaging-permission selector; see [ActiveMQ client connections](backend-mq-connections.md).

`MskTopicWriteConfig` requires a concrete topic name; `MskTopicReadConfig` additionally requires a consumer group. `MskConfig` exposes broker placement fields. See [MSK topic connections](backend-msk-connections.md) for name constraints and runtime prerequisites.

DocumentDB IAM client connections use the typed empty config; the service's `engine_version` selects the supported cluster version. No database password or IAM permission selector is exposed by this relationship. See [DocumentDB client connections](backend-documentdb-connections.md).

`app/models/` contains request models, typed service configuration, the generation IR, persistence models, and API response models.

## Input models

`app/models/input_models/` is a package, not a monolithic model file. `_general.py` defines cross-cutting models:

- `ServiceType` includes generated services and icon-only catalog services.
- `ResourceInstance` has optional stable `id`, `name`, `service_type`, a typed service config, and Terraform-variable overrides.
- `Connection` has source/target names plus optional `source_id`/`target_id`, `connection_type`, and `connection_config`.
- `EnvironmentConfig`, `GlobalTerraformConfig`, and `ArchitectureDescription` complete the generation request.

Every generated service has a dedicated config model, such as `lambda_config.py`, `eventbridge_config.py`, or the Bedrock-family models. `ResourceInstance` resolves a plain incoming config object to the registered typed model. `TerraformField` metadata on these models supplies the frontend schema and backend validation rules.

Resource names are validated for Terraform-safe syntax and uniqueness. Stable IDs let connection endpoint resolution survive a rename.

`Ec2LaunchTemplateConfig` models reusable EC2 launch settings independently of Auto Scaling: image, instance type, security groups, and optional key pair, user data, and instance profile. It intentionally has no subnet field; Auto Scaling owns workload subnet selection. Its `ec2-launch-template` service type is registered for generation, schema discovery, and editor placement.

`BatchJobDefinitionConfig` models EC2 single-container job settings independently of `BatchConfig` compute environments. It exposes native external-secret and plaintext environment maps, rejects reserved names and unsupported fields, and requires an execution role when external secret bindings are configured. Managed injection uses the typed `BatchSecretConfig` environment-name selector and a private generation flag.

## Connection and response models

`app/models/connection_configs/` defines editable connection configuration and schema response models. The connection-handler registry is the source of truth for valid service pairs and connection types.

`connection_previews.py` models connection contributions and warnings returned by the preview endpoint. `response_models.py` contains typed generation, variable-schema, and naming-rule responses. OpenAPI import has dedicated request/response models under `app/services/openapi/models.py`.

## IR models

`app/models/ir_models.py` is the internal boundary between validation and generation.

- `ProjectIR` contains environments, service modules, normalized connections, and global configuration.
- `ResourceInstanceIR` retains typed config, Terraform variables, effective provider Region, connections, and collected IAM statements.
- `ConnectionIR` preserves source/target names and stable IDs.
- `ConnectionContribution` carries `ModuleInput`, `ModuleOutput`, `ModuleResource`, and `IAMGrant` values from handlers to the assembler.
- `GenerationSummary` and `FileTree` represent generated output.

## Diagram and persistence models

`DiagramStateInput` validates persisted diagram requests. Diagram storage is versioned and upgraded through `services/diagram_migrations.py` when read. The current format is a discriminated canvas-object union covering architecture blocks, lines with anchors and waypoints, geometric/text/UML objects, typed visuals, connectors, groups, viewport, global configuration, and routing mode. Partial resource and connection configurations are shape-validated against their registered backend models while drafts may omit required generation fields. See `frontend/src/types/serialization.ts` for the client serialization contract.

Persistence records (`UserRecord`, `DiagramRecord`, and `DiagramSummary`) live in `app/persistence/models.py`.

`connection_configs/workflows.py` defines the typed `state_name` selector for Step Functions secret tasks. `workflow_states.py` validates supported JSONPath Pass placeholders; a private connection-derived flag enables workflow mutation during generation.

`connection_configs/secrets.py` defines the typed ECS injection fields. ECS generation uses a private connection-derived flag to select native injection rendering; it is not a user-editable service field.

`connection_configs/storage.py` supplies `S3NotificationConfig` for Lambda, SNS, and SQS object notifications. It exposes created/removed/restored event categories and optional key prefix/suffix filters, rejects empty or unsupported event selections, and normalizes repeated events. `S3LambdaConfig` remains a compatibility name. Connection field schema defaults accept string lists so the API can describe multi-select defaults without frontend derivation. `ModuleOutput` optionally declares resource dependencies for policy-ready references.

`EfsLambdaMountConfig` describes a single Lambda access-point mount, with non-root POSIX IDs and read-only access by default. `EbsAttachmentConfig` describes an additional Linux device; the connection validates uniqueness across the architecture and handles Availability Zone references in the backend.

`DataSyncS3LocationConfig` (`datasync-s3-location`) models a reusable S3 transfer location with an external bucket access role, subdirectory, and explicit read/write access mode. Tasks continue to support external source/destination location ARNs.

CodePipeline accepts `stages_json`, validated and normalized by typed `PipelineStage`/`PipelineAction` models, plus external artifact bucket/key fields. Nonempty pipelines require at least two unique stages and a source-first stage. The editor uses its existing string field; parsing and defaults remain backend-owned.

EFS runtime connections use `EfsEc2MountConfig`, `EfsEcsMountConfig`, and `EfsEksMountConfig` in `connection_configs/efs.py`. They extend the shared access-point UID/GID and access fields with runtime paths, optional helper installation, container selection, or Kubernetes claim identity and an external node role. EC2 exposes shell `user_data`; ECS exposes task subnet/security-group placement and public-IP selection; EKS exposes CSI add-on ownership and optional version pinning. See [EFS runtime connections](backend-efs-connections.md).

`DatabaseIamAuthConfig` requires an explicit `database_user` without IAM wildcard syntax. RDS/Aurora models carry a private connection-derived IAM flag and expose the independent `manage_master_user_password` option, defaulting to false. See [relational database connections](backend-database-connections.md).

`KeyspacesTableAccessConfig` and `TimestreamTableAccessConfig` in `connection_configs/table_access.py` require an existing table name with service-specific syntax and no IAM wildcards. They are exposed through connection schemas without service-model or bundled-variable-schema changes. See [table connections](backend-table-connections.md).

`NeptuneConfig` exposes optional `engine_version` and carries a private connection-derived `_iam_graph_access` flag. Graph connections use the typed empty config; shared version compatibility logic requires engine 1.2.0.0 or newer. See [Neptune graph connections](backend-neptune-connections.md).

`MemoryDbIamConfig` requires an existing `user_name`, validates its syntax, and normalizes it to lowercase. `MemoryDbConfig` exposes optional `engine_version` and carries a private connection-derived flag for native IAM client checks. See [MemoryDB connections](backend-memorydb-connections.md).

`OpenSearchIndexAccessConfig` requires a concrete lowercase index name without path, wildcard, or list syntax. `OpenSearchConfig` carries a private connection-derived flag for native index-client settings; connection fields are exposed dynamically without bundled-variable-schema changes. See [OpenSearch connections](backend-opensearch-connections.md).
