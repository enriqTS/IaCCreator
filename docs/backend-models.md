# Backend Models

`EksLogsConfig` exposes five strict boolean control-plane log selections and requires at least one. `EksConfig._control_plane_logs` privately enables native rendering; no editable service fields are added. A typed destination object carries the group's ARN, class, and key setting. See [EKS control-plane logs](backend-eks-logs-connections.md).

`EcsLogsConfig` exposes container selection, stream prefix, delivery mode, and a conditionally visible bounded buffer size. Private ECS flags track application logging and caller key permissions; typed destination maps carry native identities. See [ECS application logs](backend-ecs-logs-connections.md).

`ApiGatewayLogsConfig` exposes stage selection and a single-line request-ID format. Private `ApiGatewayConfig._managed_access_log_stages` marks stage ownership; native destinations and formats travel through a typed map input. See [HTTP API access logs](backend-api-gateway-logs-connections.md).

ECS → X-Ray uses `EmptyConnectionConfig`. Private `EcsConfig._collects_xray` and `XRayConfig._managed_ecs_tracing` track collector/membership generation without adding editor fields. Typed native cluster identities travel into the group independently of Lambda identities. See [ECS X-Ray connections](backend-ecs-xray-connections.md).

Lambda → X-Ray uses `EmptyConnectionConfig` and existing tracing/filter fields. Private flags on `LambdaConfig` and `XRayConfig` track connection-owned generation without adding editor fields. The group receives a typed map of native function names and ARNs. See [Lambda X-Ray connections](backend-lambda-xray-connections.md).

`EventBridgeKinesisConfig` adds optional bounded dot-notation partition-key paths to the shared invocation config. See [EventBridge Kinesis connections](backend-eventbridge-kinesis-connections.md).

`EventBridgeInvocationConfig` shares target identifiers and bounded JSON input validation between SNS and Step Functions targets. See [EventBridge workflow connections](backend-eventbridge-workflow-connections.md).

Lambda → SQS/SNS `dead_letters_to` uses `EmptyConnectionConfig`; retry and retention settings remain separate. See [Lambda dead-letter connections](backend-lambda-dead-letter-connections.md).

`SqsDeadLetterConfig` provides an integer `max_receive_count` from 1–1,000, defaulting to 5. See [SQS dead-letter connections](backend-sqs-dead-letter-connections.md).

SQS → ECS `consumed_by` uses `EmptyConnectionConfig`; polling behavior stays in application code. See [SQS to ECS polling](backend-sqs-ecs-connections.md).

`DmsSecretEndpointConfig` shares endpoint identity fields and requires full secret and external access-role ARNs; clear-text credential fields are rejected. The shared `certificate_arn` field references an imported Oracle auto-login wallet for Oracle endpoints.

`ElastiCacheServerlessConfig` models the separate Valkey/Redis cache; `ServerlessCacheIamConfig` selects an existing IAM user ID. See [serverless IAM clients](backend-elasticache-serverless.md).

`DmsIamEndpointConfig` requires an endpoint identifier, existing database user/name, and imported DMS CA certificate ARN. `DmsReplicationTaskConfig` requires a task ID, source/target endpoint IDs, source schema, and a comma-separated explicit table list; optional destination schema/prefix fields validate resulting identifier lengths. `migration_type` selects full load or CDC; CDC-only mode requires a native binlog position, PostgreSQL WAL LSN, SQL Server LSN, or positive decimal Oracle SCN, checked against the resolved source engine. `DmsSecretSourceEndpointConfig` adds optional PostgreSQL slot/plugin fields and an Oracle CDC reader selector; named slots require an explicit plugin, and CDB/PDB CDC requires Binary Reader. Oracle CDC source schema/table identifiers are limited to 30 ASCII bytes. `DmsCdcPolicy` shares engine-family position, authentication, and minimum-version requirements between validation and Terraform generation. Normalization and validation remain backend-owned. See [DMS relational endpoints](backend-dms-connections.md).

ElastiCache `connects_to` uses the typed empty connection config. Service fields select a standalone Redis or Memcached cluster and existing parameter/network resources. `transit_encryption_enabled` opts Memcached into TLS with cross-field prerequisite validation; see [ElastiCache client connections](backend-elasticache-connections.md).

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

`BatchConfig` can now name an optional job queue backed by its compute environment. Its queue name and priority are validated by the backend; the EventBridge Batch target fills a deterministic queue name when the user leaves it unset.

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

`CognitoAppSyncConfig` selects default/additional authentication, generated-client filtering, and default field access. `AppSyncConfig` carries private typed `CognitoUserPoolBinding` values for generation; these do not add editable service fields. See [Cognito AppSync authentication](backend-cognito-appsync-connections.md).

`CognitoApiGatewayConfig` selects an existing route by method/path and optionally supplies comma-separated OAuth scopes. `ApiGatewayConfig` holds private typed `CognitoJwtRouteBinding` values for generation. Omitted scopes inherit API route settings; empty scopes explicitly permit tokens without scopes. See [Cognito API Gateway authorization](backend-cognito-api-gateway-connections.md).

`CognitoLoadBalancerConfig` selects an HTTPS listener port and application hostname, built-in OAuth scopes, unauthenticated-request behavior, and bounded session duration. `CognitoListenerBinding` carries resolved pool/target/settings and derives callback/client/cookie names. `CognitoConfig.domain_prefix` optionally enables a hosted user-pool domain. See [Cognito ALB authentication](backend-cognito-load-balancer-connections.md).

`PrivateCertificateConfig` selects automatic, RSA 2048, or ECDSA P-256/P-384 certificate keys. `AcmConfig` stores a private typed `PrivateCertificateBinding` for issuance rendering; service schemas remain unchanged. Shared CA key/signature sets drive binding validation and native guards. See [Private CA certificate connections](backend-private-certificate-connections.md).

`ClientVpnCertificateConfig.certificate_role` selects `server`, `client_trust`, or `both`. `ClientVpnConfig` privately tracks the connected native ARN fields for endpoint guard rendering; existing external certificate inputs remain available. See [Client VPN certificate connections](backend-client-vpn-certificate-connections.md).

`ApiGatewayCertificateConfig` requires a normalized `domain_name` and optionally selects `stage_name` and `api_mapping_key`. Frozen `ApiGatewayDomainBinding` records hold resolved certificate/stage/path selections and deterministic resource identifiers. Service schemas stay unchanged; connection schemas expose the settings. See [API custom-domain connections](backend-api-gateway-certificate-connections.md).

`CertificateDnsConfig.ttl` supplies bounded validation-record TTLs. Frozen `CertificateDnsBinding` and `CertificateDnsRecord` values resolve canonical domains, zone selection, and shared certificate ownership. `AcmConfig` privately tracks managed DNS validation without changing service schemas. See [ACM DNS-validation connections](backend-certificate-dns-connections.md).

CloudTrail `logs_to` uses `EmptyConnectionConfig`. `CloudTrailConfig` privately tracks managed CloudWatch delivery for generator rendering; no new editable service fields or bundled-schema changes are required. See [CloudTrail logging connections](backend-cloudtrail-logs-connections.md).

AWS Config → SNS `notifies` uses `EmptyConnectionConfig`. `AwsConfigConfig` privately tracks managed notifications for native delivery-channel rendering; the connection adds no editable service fields. See [Config notification connections](backend-aws-config-sns-connections.md).

Managed Grafana → Managed Prometheus and CloudWatch `queries` use `EmptyConnectionConfig`; Timestream `queries` reuses the required `TimestreamTableAccessConfig` selector. `ManagedGrafanaConfig` privately tracks connection-managed data-source access; generation derives customer-managed permission mode without adding editable service fields. `GrafanaSourceContribution` and `GrafanaDataSource` define the shared contribution contract for independently implemented sources, including conditional IAM statement expressions and preview issues. CloudWatch's typed identity map carries group ARN, name, Region, KMS key ARN, and class into the workspace module. Timestream's typed map carries database ARN/name, native Region, and selected table name. `GrafanaOpenSearchConfig` requires a concrete default index and defaults its date field to `@timestamp`. Its typed identity map includes the native domain ARN, endpoint, name, Region, engine version, and explicit-index setting. `OpenSearchConfig` privately tracks Grafana query access without exposing generated settings as service inputs. `GrafanaAthenaConfig` requires existing Glue database/table selectors in the default regional catalog; its typed map includes native workgroup identities and enforced result settings. Result-location validation is connection-specific and adds no editable Athena service fields. See [Grafana Prometheus connections](backend-grafana-prometheus-connections.md), [Grafana CloudWatch Logs connections](backend-grafana-cloudwatch-connections.md), [Grafana Timestream connections](backend-grafana-timestream-connections.md), [Grafana OpenSearch connections](backend-grafana-opensearch-connections.md), and [Grafana Athena connections](backend-grafana-athena-connections.md).

`GrafanaRedshiftConfig` requires existing database/user selectors with conservative lowercase ASCII identifier validation. `RedshiftConfig` privately tracks managed query access and exposes optional bounded `number_of_nodes`; the typed workspace map includes native cluster identity and administrator username for override guards. See [Grafana Redshift connections](backend-grafana-redshift-connections.md).

Managed Grafana → X-Ray uses `EmptyConnectionConfig`. Its typed `xray_groups` map includes native ARN, name, Region, filter expression, and Insights enablement. Connection-specific validation requires concrete non-reserved group names and nonempty filters without adding editable service fields. See [Grafana X-Ray connections](backend-grafana-xray-connections.md).

`EksPrometheusConfig` requires whole-second intervals from 30–3600 and defaults to 60. EKS exposes optional `authentication_mode` and `endpoint_private_access`; connected collection defaults them to `API_AND_CONFIG_MAP` and true. `ManagedPrometheusConfig` privately tracks agentless-scraper tagging. A typed destination map carries native workspace ARNs and intervals into the EKS module. See [EKS Prometheus connections](backend-eks-prometheus-connections.md).

`EcsPrometheusConfig` exposes strict integer collection intervals (10–3600, default 60) and an optional application scraping port (0–65535, default 0 disables scraping). `EcsConfig` privately tracks sidecar composition and task-role attachment. Typed destination and settings inputs carry native workspace identities and shared collection settings; no new editable ECS service fields are introduced. See [ECS Prometheus connections](backend-ecs-prometheus-connections.md).
