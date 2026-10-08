# ECS Prometheus connections

ECS → Managed Prometheus (`sends_metrics`) adds an ADOT sidecar to the task definition represented by the ECS node. This collects that task's container/resource metrics through its metadata-v4 endpoint, rather than discovering other tasks in the cluster. Linux Fargate is the supported deployment mode; collection defaults unset launch type to Fargate and uses platform `LATEST`. Source tasks need subnet and security-group placement, supplied by external IDs or managed placement connections. The editor discovers settings through `/api/connection-schemas`.

`EcsPrometheusConfig` exposes two integer fields:

| Field | Default | Meaning |
| --- | --- | --- |
| `collection_interval_seconds` | 60 | Task metric collection and optional application scraping frequency, from 10–3600 seconds |
| `application_metrics_port` | 0 | Optional plain HTTP `127.0.0.1:<port>/metrics` endpoint within the task; 0 disables application scraping |

Each ECS task gets one collector, even with multiple workspace destinations. All connections from one task must use identical settings; duplicates are idempotent and conflicting settings are rejected. Different tasks can use independent settings while writing to the same workspace. Application scraping needs an instrumented application exposing its endpoint on the selected port. Metadata collection needs a running task but no application instrumentation. The [receiver documentation](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.156.0/receiver/awsecscontainermetricsreceiver) describes metadata-v4 prerequisites and available metrics.

The sidecar uses `public.ecr.aws/aws-observability/aws-otel-collector:v0.49.0`, reserves 64 CPU units and 256 MiB, and is nonessential so a collector failure does not stop application containers. Keep its reserved `iac-prometheus-collector` name out of caller-provided `container_definitions`. Budget application CPU and memory alongside the sidecar; Terraform checks declared CPU reservations and memory limits/reservations against total task capacity. Actual workload consumption still needs appropriate sizing. The default placeholder application must be replaced with a suitable long-running application before production deployment. The pinned [ADOT release](https://github.com/aws-observability/aws-otel-collector/releases/tag/v0.49.0) supports the generated configuration and environment provider; update the implementation and startup verification together when upgrading it.

The task receives configuration as `AOT_CONFIG_CONTENT` and runs `--config=env:AOT_CONFIG_CONTENT`; no image rebuild, Parameter Store config object, or config upload is required. Configuration includes the ECS metadata receiver, optional Prometheus receiver, memory limiting, ECS resource detection, batching, and one SigV4 remote-write exporter per destination. ECS resource attributes become metric labels, separating task identities while increasing cardinality and ingestion costs. No OTLP listener or CloudWatch metrics exporter is configured. See [OpenTelemetry configuration providers](https://opentelemetry.io/docs/collector/configuration/) and [AWS ECS metric ingestion](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-onboard-ingest-metrics-OpenTelemetry-ECS.html).

Native workspace ARNs, endpoints, and ARN-derived Regions travel into a typed map in the ECS module. Terraform guards verify ARN syntax, native endpoint/signing identity, identical account/partition/Region, integer settings, reserved container ownership, task capacity, Fargate launch type, and network placement. These guards also check module overrides. Same-Region native references continue to work when the whole environment changes Region. ECS collection does not require the `AMPAgentlessScraper` workspace tag or an AWS-managed scraper resource. The destination can simultaneously receive EKS scraper metrics and serve Grafana readers.

The existing ECS-owned role grants only `aps:RemoteWrite` on the connected native workspace ARNs for this integration. Task definitions attach it as both task and execution role, consistent with the existing ECS secret-injection implementation. Application containers therefore share the role's remote-write permission. Existing ECS base grants for image pulls and log streams remain; this connection adds no Prometheus query, discovery, assume-role, CloudWatch metric, or service-linked-role permissions. The deployment identity creates the diagnostic log group, so runtime log-group creation permission is unnecessary. See [AWS task versus execution roles](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html).

The collector log group belongs to the ECS module at `/aws/ecs/<node>/prometheus`, with 30-day retention. Tasks need network access to CloudWatch Logs and Prometheus; pulling the public image requires public-registry reachability. Private tasks normally need suitable egress, and private ECR endpoints alone cannot serve a public ECR image. Network rules, routes/endpoints, image mirroring, service availability, capacity, dashboards, alerts, and high-availability deduplication remain operational responsibilities. No application health dependency waits for the nonessential sidecar.

Container composition preserves existing application properties, secret injection, and EFS mount points, then appends the collector. Existing lifecycle guards remain alongside collection guards. Collector containers receive neither application secret bindings nor EFS mounts. Removing the connection removes its sidecar and diagnostic log group from generated Terraform; preserve logs separately when needed.

The ECS module exports `prometheus_collector_configuration` and `prometheus_collector_log_group`. For an ECS node named `application`, inspect the generated environment's outputs:

```sh
terraform output -json application > application-outputs.json
jq '.prometheus_collector_configuration' application-outputs.json
jq '.prometheus_collector_log_group' application-outputs.json
```

Apply Terraform, run the service with its real application containers, and inspect collector logs and workspace metrics. The connection preserves `ecs_desired_count`; configure a nonzero desired count when deploying the service. [Grafana Prometheus connections](backend-grafana-prometheus-connections.md) provide query settings for manual application in Grafana. Local tests validate generated HCL and configuration and exercise collector startup against mock metadata and a local exporter; they do not verify live AWS reachability or ingestion.
