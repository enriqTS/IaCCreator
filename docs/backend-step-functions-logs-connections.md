# Step Functions execution logging

`Step Functions → CloudWatch` (`logs_to`) configures execution-event logging for Standard and Express workflows. `StepFunctionsLogsConfig` selects `ALL` (default), `ERROR`, or `FATAL`, with `include_execution_data` defaulting to false. Payload inclusion requires a real boolean. `OFF` is excluded because an active connection must deliver logs; remove the connection to leave logging unconfigured. The API accepts one destination per workflow. Repeated connections must select the same group and settings. Multiple workflows may share a group. [AWS defines the logging configuration fields and destination limit](https://docs.aws.amazon.com/step-functions/latest/apireference/API_LoggingConfiguration.html).

## Resources and permissions

The workflow module receives a typed `workflow_logs` object containing the group's native ARN and class plus the selected settings. `StepFunctionsGenerator` renders `logging_configuration` after existing task transformations, preserving their final definition, lifecycle guards, and policy dependencies. Delivery ARNs normalize the group ARN and append exactly one `:*`, as required by the [native destination API](https://docs.aws.amazon.com/step-functions/latest/apireference/API_CloudWatchLogsLogGroup.html). `execution_log_destination` exports that delivery ARN.

The connected CloudWatch module owns the group, retention, tags, class, and encryption. The connection exports its actual class and creates no additional group or CloudWatch delivery resource policy. AWS manages the delivery resource policy through its log-delivery APIs. Native references and workflow-owned policy dependencies ensure storage and permissions exist before state-machine creation.

`execution_logs.tf` owns one `aws_iam_role_policy.workflow_logs`, attached to the workflow's existing external `role_arn`. Paths are preserved in the supplied ARN; attachment uses the final role name. `name_prefix` prevents inline-policy name collisions when workflows share a role. The connection creates no role and grants no unrelated application credentials. Shared roles accumulate permissions from all their policies; selecting a destination does not isolate workflows sharing the same role.

The inline policy separates two stream actions from eight management actions. `logs:CreateLogStream` and `logs:PutLogEvents` name only the connected group's log streams. Delivery creation/read/update/delete/list, resource-policy management/discovery, and group discovery require `Resource: "*"`. Those permissions allow wider account operations and cannot honestly be presented as destination-scoped. The split follows the [CloudWatch Logs service authorization table](https://docs.aws.amazon.com/service-authorization/latest/reference/list_logs.html).

The deployment identity must read the external role with `iam:GetRole`, attach inline policies, and pass it to Step Functions. Role trust, permission boundaries, and existing explicit denies remain externally managed. Native role partition/account checks and an exact ARN comparison against the resolved IAM role run on the policy resource before attachment, preventing a foreign or mistyped-path ARN's basename from selecting a local role. The lookup uses the [provider's IAM role data source](https://github.com/hashicorp/terraform-provider-aws/blob/main/website/docs/d/iam_role.html.markdown).

## Encryption and guards

Managed CloudWatch keys reuse the existing key-owned regional Logs service statement, scoped by the exact log-group encryption context. The workflow's log policy receives no KMS grant. External key owners must authorize the regional Logs service. State-machine definition/history encryption uses separate permissions and is outside this connection. [AWS distinguishes log-group encryption from state-machine encryption](https://docs.aws.amazon.com/step-functions/latest/dg/encryption-at-rest.html).

Backend validation rejects missing/malformed external roles, incompatible workflow types/group classes, conflicting destinations/settings, and effective Region mismatches, including environment overrides. Terraform guards cover role partition/account, native group ARN syntax and the 256-character delivery limit, group partition/Region/account, supported workflow/group classes, and enabled log levels. Standard and Infrequent Access groups are supported; Delivery-class groups are excluded. [CloudWatch documents their class capabilities](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatch_Logs_Log_Classes.html).

## Operational behavior

Execution payloads can include secret values and state inputs/outputs; enabling them is explicit. Express workflows do not retain Step Functions execution history. CloudWatch delivery is best effort, oversized payloads may be truncated, and log ingestion/storage is billed. `/aws/vendedlogs/states/` names help avoid delivery resource-policy size limits; existing account quotas still apply. These behaviors are documented in the [Step Functions logging guide](https://docs.aws.amazon.com/step-functions/latest/dg/cw-logs.html).

The connection composes with all eight existing service-task integrations and with Grafana queries, managed/external log encryption, and shared groups/roles. It does not add X-Ray instrumentation or state-machine customer-key encryption.

## Verification

`tests/test_step_functions_logs_connections.py` covers defaults and invalid inputs, property-based duplicates/settings, single-destination ownership, effective Regions, standalone behavior, preview prerequisites, and preservation of every existing task generator's definitions/guards/dependencies. Terraform console evaluates the actual emitted IAM policy, ARN normalization, and native override guards. Provider validation and plan graphs cover Standard/Express, Infrequent Access, duplicates, shared groups/roles, managed/external encryption, regional aliases, and Lambda/Secrets Manager/Grafana composition. API tests verify discovery of both fields. Tests make no live AWS deployment or ingestion calls.
