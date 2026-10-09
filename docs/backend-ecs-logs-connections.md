# ECS application log connections

ECS → CloudWatch (`logs_to`) configures the `awslogs` driver on a selected application container in the modeled Linux Fargate task. The editor discovers the typed connection through `/api/connection-schemas`; no frontend-specific connection logic is required.

## Settings

| Field | Default | Behavior |
|---|---|---|
| `container_name` | Empty | Selects the container named after the ECS node. An explicit name selects another application container. |
| `stream_prefix` | `ecs` | A 1–128 character prefix using letters, numbers, underscore, slash, dot, hash, or hyphen. |
| `mode` | `non-blocking` | Selects buffered delivery or blocking writes. |
| `buffer_size_mib` | `10` | A whole number from 1–64 MiB, used only for non-blocking delivery. Blocking delivery normalizes this value to zero internally. |

Log streams use `<prefix>/<container>/<task-id>`. Non-blocking delivery can discard logs when its buffer fills; blocking delivery can stall application output when delivery fails. Both behaviors and the stream naming follow the [ECS log configuration API](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_LogConfiguration.html).

Each selected container has one destination and effective delivery configuration. Distinct containers can share a group or use different groups; different ECS nodes can share a group. Identical connectors are idempotent, and conflicting assignments are rejected independently of connector order. Managed X-Ray and Prometheus collector names cannot be selected because those collectors own their diagnostic log groups.

Provide matching container names in the task's `container_definitions` Terraform input. The generator merges only `logConfiguration` on selected containers. Environment values, secrets, mounts, ports, and other container properties remain intact. Unselected containers retain their existing logging. Selected containers must have no manual logging configuration; null or empty configurations are accepted. Terraform preconditions reject missing or duplicate container names and conflicting logging configurations.

## Native destinations and composition

The ECS module receives a typed `ecs_logs` map containing native log-group ARNs, stream prefixes, modes, and buffer sizes. ARN parsing supplies the group name and Region, avoiding copied identifiers. Native guards check ARN shape and common partition, account, and Region. Generation and preview also check effective Regions and Fargate network placement.

Application logging is composed after secret injection and EFS mounts, before X-Ray and Prometheus collectors. Collector logging remains unchanged. Task memory must cover application memory reservations, managed collector reservations, and every non-blocking application log buffer. The guard includes both collectors when present; a task sized exactly for the collectors needs additional memory for application buffering. Real application runtime overhead remains a sizing concern.

An unset launch type becomes Fargate. Existing service desired count and network settings remain in place. Supply real application images, a nonzero desired count, suitable task CPU/memory, and access to CloudWatch Logs and the image registry before deployment. Managed subnet/security-group connections or external IDs provide placement.

The CloudWatch module owns group creation, retention, class, and encryption. `awslogs-create-group` is explicitly false. The ECS module exports `application_log_configurations` and does not add a second application log group. Group references flow into ECS without a reverse dependency, including with Grafana queries and managed encryption.

## Execution permissions and encryption

The task attaches the existing ECS-owned role as `execution_role_arn` and waits for its policy. Logging alone does not attach a task role or expose execution credentials to applications. Other ECS connections can reuse that same role as the task role, as before. See the [AWS execution-role distinction](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html).

The existing ECS base policy grants image pulls and `logs:CreateLogStream`/`logs:PutLogEvents` on wildcard resources. This connection reuses that policy; destination guards configure delivery and do not reduce the base IAM scope. No `logs:CreateLogGroup` grant is added.

Encrypted destinations additionally receive one ECS-owned inline execution-role policy. It grants the required encryption operations on exact key ARNs, constrained by `kms:ViaService` to regional CloudWatch Logs and by encryption context to the connected native group. A separate `DescribeKey` statement uses the same key and service scope without an encryption-context condition, which that metadata operation does not support; see [KMS least-privilege guidance](https://docs.aws.amazon.com/kms/latest/developerguide/least-privilege.html). Shared group bindings deduplicate the grant. The task waits for this policy alongside existing secret and tracing policies.

Managed keys reuse the shared KMS policy owner and its regional Logs service grant. External IDs and aliases resolve to native key ARNs through `data.aws_kms_key`; external key policies must authorize both the regional Logs service and the execution role. Key discovery and log-group provisioning permissions belong to the deployment identity. These caller permissions follow [CloudWatch Logs encryption guidance](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html). Applications that already share the execution role as a task role inherit the constrained permissions; direct KMS use is excluded by the service condition.

Application log files, FireLens, multiline parsing, log filtering/subscriptions, and automatic group creation remain separate capabilities. Log ingestion/storage costs and historical log retention remain operational concerns.

## Verification

`tests/test_ecs_logs_connections.py` covers typed defaults/bounds, shared and separate destinations, conflicts, launch/placement, effective Regions, unchanged standalone tasks, execution-role ownership, and secret-policy dependencies. Property tests check duplicate/order independence and lossless application container serialization, including Terraform template markers. Terraform console evaluates native scope, delivery settings, key/service/context permissions, ownership guards, and buffer memory. Generated plain, blocking, multiple-container, shared-group, mixed, managed/external key, and regional projects pass validation and plan dependency graphs. API endpoint tests verify connection discovery and conditional buffer visibility.
