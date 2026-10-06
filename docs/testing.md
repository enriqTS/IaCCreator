# Testing

`tests/test_cloudtrail_logs_connections.py` covers trail-owned roles/policies, native delivery readiness, effective Regions, single-destination conflicts, property-based trail sharing/order/deduplication, managed/external KMS access, S3 preview prerequisites, and unchanged unconnected trails. Terraform console checks account/Region/partition guards and exact stream/wildcard scopes; plain/shared/managed-key/external-key architectures pass validation and plan graphs. Connection-schema tests verify dynamic discovery of the typed empty config.

`tests/test_certificate_dns_connections.py` covers zone-owned validation records, typed TTLs, longest-suffix SAN coverage, public/private validation errors, wildcard/apex deduplication, repeated connections, shared cross-Region certificate records, consumer readiness, and preview prerequisites. Property tests exercise stable plan keys; Terraform console checks native overrides; generated API/VPN/CloudFront/Load Balancer/shared-certificate projects pass validation and plan graphs, and a mocked provider checks first-plan handling of unknown DNS tokens. The real connection-schema endpoint exposes the TTL field.

`tests/test_eventbridge_kinesis_connections.py` covers stream-scoped roles, partition-path generation/bounds, conflicting settings, multiple target IDs, duplicate/order independence, and Terraform validation/graphs.

`tests/test_eventbridge_sns_connections.py` covers dedicated publish-role scopes, managed/external encryption, FIFO and cross-service target-ID conflicts, idempotence, and Terraform validation/graphs.

`tests/test_eventbridge_workflow_connections.py` covers native workflow targets, scoped invocation roles, constant-input validation, identifier conflicts, duplicate/order independence, and Standard/Express Terraform validation and graphs.

`tests/test_lambda_dead_letter_connections.py` covers native SQS/SNS bindings, scoped role/key grants, destination conflicts, FIFO restrictions, unchanged defaults, order/duplicate independence, and Terraform validation/graphs across encryption modes.

`tests/test_sqs_dead_letter_connections.py` covers receive-count bounds, native references, FIFO restrictions, conflicts/cycles, shared-destination limits, duplicate/order independence, and Terraform validation/graphs for single/shared/chained queues.

`tests/test_sqs_ecs_connections.py` covers queue-scoped task-role polling permissions, native client references, managed/external KMS decrypt grants, multiple queues, duplicate/order independence, and Terraform validation/graphs.

`tests/test_dms_oracle_binary_reader.py` covers typed reader options, engine/direction restrictions, required PDB reader selection, Oracle CDC identifier boundaries, property-based SCN preservation, and Terraform validation/graphs for all four Oracle editions in both CDC modes.

`tests/test_dms_oracle_cdc.py` covers non-CDB LogMiner CDC, property-based SCN preservation, source guards, cross-engine position rejection, preview prerequisites, and Terraform validation/graphs for both CDC modes.

`tests/test_dms_oracle_connections.py` covers edition/CDB mapping, wallet references and preview guidance, IAM/missing-CDB-reader rejection, case-preserving selections, and Terraform validation/graphs for Oracle full-load sources and migration targets.

`tests/test_dms_sqlserver_cdc.py` covers native LSN bounds, cross-engine rejection, DMS version guards (including Terraform evaluation), stopped CDC modes, external prerequisites, and Terraform validation/graphs.

`tests/test_dms_sqlserver_connections.py` verifies SQL Server edition/TLS mapping, credential exclusion, IAM rejection, full-load source/target tasks, and Terraform validation/graphs for supported CDC sources targeting SQL Server.

`tests/test_dms_postgres_cdc.py` covers WAL position formats, source-only slot/plugin fields, named slot ownership, native engine guards, and Terraform validation/graphs for PostgreSQL CDC modes.

`tests/test_dms_secret_connections.py` covers secret ARN validation, credential exclusion, cross-authentication identifier conflicts, mixed-authentication full-load/CDC tasks, and Terraform validation/dependency graphs.

`tests/test_elasticache_serverless_connections.py` checks exact IAM grants, external-group requirements, user validation, native endpoint types, ARN identity, deterministic aggregation, and Terraform validation/graphs for both engines and consumers.

`tests/test_elasticache_tls.py` checks Memcached TLS prerequisite validation, Terraform-evaluated override guards, legacy disabled output, native client TLS metadata, and Lambda/ECS project validation/graphs.

`tests/test_dms_cdc_tasks.py` covers migration-mode validation, explicit binlog positions, PostgreSQL IAM source rejection, source-engine guards, preview prerequisites, and Terraform validation/graphs with naming transformations.

`tests/test_dms_table_mappings.py` verifies destination identifier limits, unchanged legacy output, explicit selection preservation, deterministic transformation IDs, and Terraform-evaluated mapping JSON and dependency graphs.

`tests/test_dms_replication_task_connections.py` checks native endpoint references, explicit mapping normalization, invalid and missing selectors, task ID conflicts, stopped task behavior, previews, and Terraform validation/dependency graphs.

`tests/test_dms_database_connections.py` covers IAM endpoint engine settings, scoped roles, version guards, identifier conflicts, deterministic aggregation, and Terraform validation/graph checks for all supported relational engines.

`tests/test_elasticache_client_connections.py` checks engine/count validation, native endpoint/TLS projection, external placement preservation, aggregation, and Terraform validation/graph checks for both standalone engines.

`tests/test_mq_client_connections.py` evaluates protocol selection with Terraform, checks policy/credential isolation and Secrets Manager composition, exercises multi-broker aggregation, and validates generated client projects and dependency graphs.

`tests/test_msk_access_connections.py` covers exact-topic/group permissions, invalid names, engine and broker-placement checks, deterministic aggregation, client metadata, and generated Terraform validation/graph checks.

`tests/test_documentdb_access_connections.py` covers runtime role identity, policy preservation, engine rejection, deterministic aggregation, preview prerequisites, and Terraform validation/graph checks for Lambda/ECS DocumentDB clients.

## Commands

From the repository root:

```text
uv run pytest -n auto
uv run ruff check .
```

From `frontend/`:

```text
pnpm vitest run
pnpm lint
pnpm build
```

## Backend

Backend tests live in `tests/`. The suite combines generator/property tests, API tests, persistence tests, connection tests, and Terraform validation tests.

Key coverage areas include:

- typed service config, TerraformField metadata, schema serialization/validation, naming rules, and option enforcement;
- IR construction, stable resource identity, generator registration, variable wiring, execution-role ownership, and generated-project Terraform validation;
- API Gateway routes, authorizers, WebSocket routes, and backend OpenAPI import;
- every registered connection, connection schemas, aggregation, previews, EventBridge targets, S3 notifications, and DynamoDB streams;
- diagram CRUD, migrations, session isolation/middleware, and TinyDB/DynamoDB factory behavior.

`tests/test_kinesis_access_connections.py` verifies stream-scoped read/write actions, runtime role attachment and exported references, read-only defaults, deterministic duplicate/multi-stream aggregation, preview guidance, and Terraform validation/plan graphs. Registry-derived tests additionally validate all four Lambda/ECS Kinesis connections and their API schema exposure.

`tests/test_codebuild_secret_connections.py` covers native injection, external-role ownership, configuration validation, binding conflicts, and legacy registry defaults. Shared secret tests exercise deterministic aggregation, IAM/KMS scoping, preview ownership, and encrypted-project Terraform validation for Batch job definitions, Step Functions, MWAA, CodeBuild, and App Runner alongside Lambda, EC2, and ECS. `tests/test_app_runner_secret_connections.py` additionally verifies runtime/image-pull role separation, reserved environment names, public-image settings, and Terraform-evaluated merging of managed and external secret bindings.

`tests/test_launch_template_connections.py` covers managed template versions, duplicate/shared connections, conflicting templates, external template compatibility, catalog/schema exposure, and a complete VPC/subnet/security-group/route/Auto Scaling architecture validated by Terraform. `tests/test_placement_external_identifiers.py` derives cases from all list-placement registry entries and uses permutations to verify preservation of external IDs and deterministic repeated generation.

`tests/test_mwaa_secret_connections.py` verifies external execution-role ownership, missing-role rejection, empty read-access configuration, and absence of native injection or plaintext retrieval. MWAA also participates in shared secret aggregation, preview, KMS, and encrypted-project Terraform validation tests.

`tests/test_kms_access_integration.py` covers consumer-action KMS grants, shared service policies, external-key warnings, encryption flags, key conflicts, and mixed-service Terraform validation/plan graphs. `tests/test_iam_template_references.py` verifies that policy ARN placeholders evaluate to real values and foreign resources use module inputs.

`tests/test_step_functions_secret_connections.py` verifies executable SDK tasks, scoped external-role access, invalid placeholder/config rejection, sensitive-data warnings, and unchanged unconnected workflows. Terraform console tests evaluate task definitions and environment-override guards, preserving transitions, data paths, and unrelated workflow states.

`tests/test_step_functions_batch_connections.py` covers synchronous jobs, scoped submission and monitoring permissions, invalid targets and settings, mixed-task conflicts, deterministic composition, Terraform console state evaluation, and generated-project validation/graphs.

`tests/test_step_functions_sns_connections.py` covers Publish states, standard/FIFO settings, scoped topic and KMS permissions, state conflicts, deterministic composition, Terraform console evaluation, and generated-project validation/graphs.

`tests/test_step_functions_sqs_connections.py` covers SendMessage states, queue URL/ARN separation, standard/FIFO settings, scoped queue and KMS permissions, mixed-task conflicts, deterministic composition, Terraform console evaluation, and generated-project validation/graphs.

`tests/test_step_functions_dynamodb_connections.py` covers all four optimized item operations, JSONPath and expression validation, per-operation table IAM and KMS scopes, mixed-task conflicts, deterministic composition, Terraform console evaluation, and generated-project validation/graphs.

`tests/test_step_functions_eventbridge_connections.py` covers default and custom event buses, input and constant JSON details, bus-scoped PutEvents IAM, mixed-task composition, placeholder validation, Terraform console evaluation, and generated-project validation/graphs.

`tests/test_appsync_lambda_connections.py` covers direct resolvers, API-scoped role trust, function-scoped invocation policy, data-source sharing, deterministic multi-function output, conflicting field selection, name collisions, schema requirements, and Terraform validation/graphs.

`tests/test_appsync_dynamodb_connections.py` covers four item operations, JavaScript key mapping, operation-scoped IAM, managed/external KMS references, data-source sharing, duplicate and cross-service field conflicts, invalid config, and Terraform validation/graphs.

`tests/test_appsync_opensearch_connections.py` covers index-scoped document resolvers and IAM, field conflicts, invalid index names, deterministic sharing, and Terraform validation/graphs.

`tests/test_appsync_eventbridge_connections.py` covers default/custom bus publishers, event metadata, failed-entry handling, shared data sources, field conflicts, and Terraform validation/graphs.

`tests/test_appsync_aurora_connections.py` covers Data API cluster wiring, scoped database-user secrets, row operations, field conflicts, invalid config, and Terraform validation/graphs.

`tests/test_cognito_appsync_connections.py` covers default/additional providers, client filtering, API-key behavior, provider conflicts, property-based aggregation/deduplication, cross-Region references, preview guidance, resolver composition, and Terraform validation/graphs. The connection-schema endpoint tests verify the editor receives the typed authentication settings.

`tests/test_cognito_api_gateway_connections.py` covers JWT issuer/audience references, exact route selection, property-based authorizer sharing/deduplication, scope inheritance/overrides, native and Lambda integration composition, order independence, authentication conflicts, Region overrides, preview guidance, and Terraform validation/graphs. Connection-schema tests verify the route and scope settings served to the editor.

`tests/test_cognito_load_balancer_connections.py` covers ordered HTTPS authentication/forwarding, native references, confidential/public client separation, domain generation, property-based order/deduplication, selected listeners, callback normalization, isolated cookies, invalid/conflicting bindings, inherited/overridden Regions, previews, and Terraform validation/graphs. Connection-schema tests verify the editor's typed authentication settings.

`tests/test_private_certificate_connections.py` covers root signing/activation, account-scoped ACM renewal permissions, dependency-ready outputs, native private issuance, public validation suppression, algorithm compatibility, property-based CA sharing/order/deduplication, issuer conflicts, effective Regions, listener composition, CloudFront trust rejection, and previews. Terraform console evaluates passing/failing usage, signing, key, and Region guards; generated RSA/ECDSA projects pass validation/graphs. Connection-schema tests verify the key choices served to the editor.

`tests/test_client_vpn_certificate_connections.py` covers server/client CA/combined roles, private CA composition, public issuance readiness, external role preservation, property-based waiter/input sharing, separate issuer references and naming collisions, conflicting assignments, unsupported keys/client trust, effective Regions, schema defaults, and previews. Terraform console checks native key/Region guards; generated projects pass validation and dependency graphs. Connection-schema endpoint tests verify role choices.

`tests/test_api_gateway_certificate_connections.py` covers domains/stage/path mappings, public/private readiness, shared Client VPN issuance, property-based aggregation and identifier collisions using the shared DNS-label strategy, certificate SAN/wildcard coverage, ownership/mapping conflicts, existing manual domains, HTTP/WebSocket stages, mutual TLS prerequisites, effective Regions, and previews. Terraform console evaluates native hostname/Region/account guards; API projects compose with Cognito/Lambda and pass validation/graphs. Connection-schema tests verify the editor's mapping settings.

`tests/test_batch_secret_connections.py` covers job/execution-role separation, native settings and reserved-name validation, external bindings, catalog/schema exposure, and unchanged compute-environment compatibility. Terraform console tests evaluate container properties, resource requirement types, plaintext-variable replacement, and managed/external secret merging. Shared tests cover aggregation and encrypted-project validation.

`conftest.py` provides Hypothesis strategies and shared helpers. New generator or serialization tests should extend those strategies where possible.

Any fixture that creates a `TestClient` from the real `app.main.app` must isolate persistence: monkeypatch `app.persistence.factory.get_repository`, reload `app.main`, and override `app.routers.diagrams.get_repo` through `app.dependency_overrides`. This prevents parallel workers from writing the real TinyDB file.

## Frontend

Frontend tests live in `frontend/__tests__/` and `frontend/src/utils/__tests__/`.

Property tests cover canvas-object creation/deletion/serialization, grouping, history, anchors, snapping, selection, placement, routing, line waypoints and segments, viewport transforms, sidebar search/pinning, and configuration visibility. Unit tests cover components, Zustand behavior, persistence/API clients, schema and connection panels, API Gateway editing, routing grid/pathfinder/router behavior, shortcuts, and tours.

Routing tests are split between the legacy deterministic routing helpers and the current `utils/routing/` grid/pathfinding implementation. Keep both suites when changing fallback behavior.

Use behavior-oriented tests rather than source-text assertions. For geometry and interaction changes, mutation-test the relevant rule when practical: deliberately break it, confirm the new test fails, then restore it.

`tests/test_s3_notification_connections.py` covers shared bucket notification ownership, external destinations, deterministic duplicates, converging SNS/SQS publishers, FIFO rejection, external-key warnings, shared KMS policies, filter conflicts, and preview ownership. A mixed architecture passes Terraform validation and plan-graph checks; registry-derived validation covers each new notification pair. Schema endpoint tests verify list-valued event defaults for all three destinations.

`tests/test_aws_config_sns_connections.py` covers native channel/status ordering, policy-ready topic ARNs, retained owner permissions, scoped Config identities, property-based shared Config/S3 policies, duplicate/order independence, unsupported FIFO/encrypted destinations, effective Region checks, preview prerequisites, and unchanged standalone generation. Terraform console checks exercise native guards, including cross-account acceptance; Terraform validation and plan graphs cover standalone and shared S3 delivery. Registry and schema endpoint tests cover catalog discovery and minimal generation.

`tests/test_s3_eventbridge_connections.py` covers managed rule scoping, preserved filters, unsupported buses/schedules/patterns, duplicate and converging bucket connections, mixed direct notifications, preview ownership, and Terraform validation/plan graphs.

`tests/test_ebs_attachment_connections.py` covers volume-owned attachments, managed Availability Zone references, invalid/root device rejection, Linux device aliases, duplicate/multiple volume connections, unsupported Multi-Attach, preview guidance, and Terraform validation/plan graphs.

`tests/test_efs_lambda_connections.py` verifies access-point ownership, Lambda native mount blocks, filesystem-scoped permissions, network prerequisites, invalid bindings, shared filesystems, and generated-project Terraform validation. Existing EFS subnet and security-group placement supply its mount-target networking.

`tests/test_backup_selection_connections.py` covers all five resource types, exact ARN selection, role validation and conflicts, deterministic duplicates, preview ownership, and a mixed Terraform project. Shared fixtures now supply RDS/Aurora identifiers and Aurora's required engine for registry-derived validation.

`tests/test_s3_location_connections.py` verifies Athena/Lake Formation module references and prefixes, conflicting locations, idempotent duplicates, role requirements, external fallback fields, and preview guidance. Both pairs participate in registry-derived Terraform validation.

`tests/test_s3_replication_connections.py` covers versioning dependencies, deterministic multi-destination rules, external destinations, role conflicts, managed KMS references, cross-Region wiring, and Terraform validation/plan graphs.

- `test_s3_log_delivery_connections.py`: shared audit bucket policy scope, duplicate/order invariance, single-destination validation, and Terraform validation/dependency graph.

- `test_s3_read_source_connections.py`: MWAA/Comprehend native references, read policies, external-role requirements, versioning, managed-key grants, duplicate handling, and Terraform graphs.

- `test_firehose_s3_connections.py`: native delivery configuration, policy scope, duplicate connections, invalid destinations/roles, and encrypted Terraform validation/graph.

- `test_cloudfront_s3_connections.py`: signed REST origins, read-only permissions, origin cardinality, shared audit/KMS policies, deterministic aggregation, and cycle-free Terraform graphs.

- `test_datasync_s3_connections.py`: standalone locations, directional IAM, location cardinality, encryption, idempotence, and complete transfer Terraform graphs.

- `test_codepipeline_s3_connections.py`: typed stage JSON validation, artifact ownership, duplicate handling, unsupported region overrides, and encrypted pipeline Terraform graphs.

- `test_efs_ec2_connections.py`: shared secret/mount role ownership, shell user-data validation and escaping, rendered bootstrap shell syntax, instance replacement, and Terraform validation/graphs.
- `test_efs_ecs_connections.py`: native TLS/IAM volumes, read/write grants, path conflicts, deterministic bindings, composed container mounts/secrets evaluated by Terraform, and Terraform validation/graphs.
- `test_efs_eks_connections.py`: static claim manifests, supported CSI access modes, add-on ownership, node-role grants, claim conflicts, stable storage identity across workload path edits, and Terraform validation/graphs.

`test_database_access_connections.py` covers user/resource-scoped IAM grants, unsupported engines and usernames, explicit credential-management opt-in, duplicate/multiple-user aggregation, runtime metadata, Terraform validation/graphs, and Terraform-evaluated ARN partition/Region/account/resource-ID correctness. Registry fixtures provide an explicit application database user and supported engine for all four login connections.

`test_table_access_connections.py` verifies Keyspaces/Timestream table-scoped actions, separate system-metadata/endpoint-discovery permissions, required and validated selectors, role attachment, multi-table/read-write aggregation, runtime metadata, and Terraform validation/graphs. Terraform console checks evaluate table and system ARNs using the target partition/account/Region and normalize Keyspaces' trailing keyspace slash. Registry-derived validation covers all eight Lambda/ECS connections.

`test_neptune_access_connections.py` covers scoped graph actions, runtime role attachment, endpoint metadata, native authentication, unchanged unconnected behavior, supported/unsupported engines, duplicate aggregation, and Terraform validation/graphs. Terraform console checks evaluate partition/Region/account/resource-ID ARNs and the shared engine-version guard. Registry-derived validation covers all four Lambda/ECS connections.

`test_memorydb_access_connections.py` covers exact cluster/user Connect grants, existing identity ownership, lowercase normalization, invalid selectors, TLS/ACL/engine prerequisites, deterministic aggregation, runtime metadata, and Terraform validation/graphs. Terraform console evaluates IAM-mode, ACL-membership, version, and TLS guards with passing and failing metadata. Registry fixtures exercise both Lambda and ECS login connections.

`test_opensearch_access_connections.py` checks method/path authorization boundaries, search POST versus mutation permissions, invalid index selectors, runtime role attachment, native domain settings, deterministic multi-index aggregation, and unchanged unconnected domains. Mixed read/write projects pass Terraform validation and dependency-graph checks; registry tests cover all four Lambda/ECS connections.
