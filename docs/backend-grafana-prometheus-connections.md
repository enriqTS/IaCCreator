# Managed Grafana Prometheus connections

Managed Grafana → Managed Prometheus (`queries`) uses the typed empty connection config and appears through `/api/connection-schemas`. Each Grafana workspace can query multiple managed Prometheus workspaces, including workspaces in other Regions of the same account and partition. Repeated identical connections aggregate deterministically. Organization role chaining and cross-account data-source roles are not modeled.

The connection generates a Grafana-owned IAM role and inline policy, deriving `CUSTOMER_MANAGED` permission mode for the workspace. AWS requires API-created workspaces to manage their own roles and permissions. The role trusts the Grafana service, constrained by the source account and Grafana Region; the workspace ID wildcard avoids a role/workspace creation cycle. The policy grants only `aps:QueryMetrics`, `aps:GetLabels`, `aps:GetSeries`, and `aps:GetMetricMetadata` on connected workspace ARNs. It grants no metric ingestion, workspace discovery, or cross-account assume-role access. Workspace creation waits for the policy.

Prometheus modules expose their native ARN, endpoint, and Region. A typed map carries these values into Grafana. Terraform preconditions validate workspace ARN syntax, account/partition scope, and endpoint/signing-Region consistency; additional workspace guards reject runtime organization or service-managed permission overrides. ARN-derived identities are used even when environment Region overrides change deployment placement.

The Grafana module exports `prometheus_data_sources`, a map of Grafana data-source API payloads keyed by diagram resource name. Payloads use the dedicated `grafana-amazonprometheus-datasource` plugin, proxy access, SigV4 default credentials, and the native Prometheus signing Region. No access keys or tokens are generated. UIDs derive from the native workspace ARN rather than the diagram resource name. Outputs wait for Grafana and its query policy to exist.

Data sources still need to be added in Grafana with an authorized Grafana identity. Install/enable the Amazon Prometheus plugin if needed, then enter the output settings in the Grafana UI or submit each payload to its data-source API. AWS workspace creation and `data_sources` selection alone do not create Grafana data-source objects. User authentication/access, metrics ingestion, dashboards, and private network access are separate prerequisites; preview states these limits. Other configured AWS data-source selections are retained and need separate IAM grants.

For a Grafana resource named `grafana` connected to a Prometheus resource named `metrics`, run these commands from the generated environment directory to extract the payload:

```sh
terraform output -json grafana > grafana-outputs.json
jq '.prometheus_data_sources.metrics' grafana-outputs.json > metrics-data-source.json
```

Send that JSON body to `POST https://<workspace_endpoint>/api/datasources` with a Grafana token authorized to create data sources, then use Save & test in Grafana. For subsequent updates, use `PUT /api/datasources/uid/<uid>` with the exported UID. See the [Grafana data-source API](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/data_source/). Token creation, external API calls, and Grafana object lifecycle are not performed by the generator.

`GrafanaDataSourcesHandler` aggregates implementations of the `GrafanaDataSource` protocol into one shared workspace role. `GrafanaPrometheusSource` owns Prometheus-specific module inputs, policy statements, native guards, and API payloads. [CloudWatch Logs connections](backend-grafana-cloudwatch-connections.md) contribute to the same role. New supported data-source implementations can contribute without expanding the workspace generator into service-specific branches. Unconnected workspace generation and public service schemas remain unchanged.

References: [AWS workspace API permission requirements](https://docs.aws.amazon.com/grafana/latest/APIReference/API_CreateWorkspace.html), [Grafana role trust guidance](https://docs.aws.amazon.com/grafana/latest/userguide/cross-service-confused-deputy-prevention.html), [Prometheus IAM actions](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amp.html), and [Amazon Prometheus plugin configuration](https://grafana.com/docs/plugins/grafana-amazonprometheus-datasource/latest/configure/).
