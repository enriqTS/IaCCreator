# HTTP API Gateway access-log connections

API Gateway → CloudWatch (`logs_to`) configures access logging on one selected HTTP API stage. It uses the connected log group's native ARN and updates the existing `aws_apigatewayv2_stage`, retaining its automatic deployment, stage variables, throttling, and route settings. The connection appears through `/api/connection-schemas` without frontend changes.

## Settings and ownership

`ApiGatewayLogsConfig` has two editable fields:

| Field | Default | Behavior |
|---|---|---|
| `stage_name` | Empty | Selects the first configured stage, or `$default` when no stages exist. A named selection must already exist on the API. |
| `log_format` | JSON containing request ID, IP, time, method, route, status, and protocol | Must be a single line containing the exact `$context.requestId` variable. Text formats are also accepted. |

The default stage is created with automatic deployment when the API has no configured stages. Existing named stages retain their deployment settings; a stage without automatic deployment still needs a separately managed deployment and usable routes. Connecting a log group does not create application routes or integrations.

Stage names must be valid AWS stage names with distinct generated Terraform identifiers. Multiple stages can share a log group or use separate groups. Multiple APIs can also share a group. Identical connections are idempotent; differing destinations or formats for the same stage are rejected independently of processing order.

The selected stage must not already use a manual destination or an API-local generated log group. Remove that configuration before adding the managed connection. Configure its format on the connection, rather than at the API or stage level. Unselected stages keep their existing local logging. Unconnected API generation is unchanged.

## Generated Terraform

The API module receives `api_access_logs`, a typed `map(object({ arn = string, format = string }))` keyed by selected stage name. The log group module owns its existing `aws_cloudwatch_log_group` and exports its native ARN. Its retention, class, and encryption remain log group settings.

The stage strips an optional `:*` ARN suffix when setting its destination and checks that the value identifies a log group. Native data sources check the destination's partition, Region, and account against the API module's provider. Generation and preview also reject incompatible effective Regions. Environment Region overrides are honored by the handler; explicitly conflicting per-resource Regions remain subject to the common IR validation rule.

Stage preconditions require HTTP protocol and a valid single-line request-ID format, including when module inputs are overridden. Literal `${...}` and `%{...}` markers in custom formats are escaped in Terraform so they remain literal log-format text.

There is no reverse reference from the log group to the API. Domains, Cognito JWT authorizers, Lambda routes, KMS encryption, and Grafana log queries compose without a module dependency cycle.

## Delivery permissions and deployment prerequisites

For HTTP APIs, AWS configures log delivery and creates or updates the destination resource policy when the deployment identity has the required permissions. The generator supplies the native stage destination; it does not manage `aws_api_gateway_account`, a competing log resource policy, or an application IAM role. The deployment identity needs the CloudWatch Logs delivery, discovery, and resource-policy permissions described in [HTTP API logging permissions](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-logging.html). Resource policy size and delivery limits can still prevent activation. See [CloudWatch log delivery policy behavior](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-CWL.html).

KMS → CloudWatch encryption connections retain their existing regional Logs service key-policy grants. External keys must authorize that service separately, as reported in preview. The API receives no KMS grant: CloudWatch Logs performs destination encryption.

Access logs incur ingestion and storage charges. Custom formats can contain sensitive metadata; choose fields and log access appropriately. Request-ID inclusion and the single-line requirement follow the [API Gateway v2 stage API](https://docs.aws.amazon.com/apigatewayv2/latest/api-reference/apis-apiid-stages-stagename.html).

## Protocol limits

This connection supports HTTP APIs. WebSocket logging requires regional account logging permissions and remains a separate implementation task. HTTP access logging does not produce execution logs or X-Ray traces.

API Gateway → X-Ray is deferred until REST API generation exists. The current generator models `aws_apigatewayv2_api` HTTP/WebSocket APIs; AWS supports API Gateway X-Ray tracing only for REST APIs, and `aws_apigatewayv2_stage` has no tracing setting. See [AWS API Gateway tracing support](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-apigateway.html) and the [provider stage arguments](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_stage).

## Verification

`tests/test_api_gateway_logs_connections.py` covers native destinations, one stage owner, shared groups, multiple stages/destinations, property-based order and duplicate independence, unchanged unselected stages, format validation, effective Regions, previews, and composition with existing API and log consumers. Terraform console evaluates native guards and literal format preservation. Generated default, named-stage, shared-group, mixed, managed/external encryption, and regional projects pass `terraform validate` and plan dependency graphs. Connection endpoint tests verify editable defaults through the real API on an isolated repository.
