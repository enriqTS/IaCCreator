# EventBridge to Step Functions

Connect an EventBridge rule to Step Functions with `targets`. The connection creates an EventBridge target and a dedicated IAM role in the rule module. The role trusts EventBridge for that rule ARN and grants `states:StartExecution` only on the connected state machine's native ARN. The target waits for the role policy. The workflow module receives no reverse references. See [EventBridge target-role permissions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-events-iam-roles.html).

`target_id` is optional and defaults to the workflow's normalized name. Identifiers must uniquely select a destination and input within a rule; duplicate identical connections are idempotent. Distinct target identifiers can invoke the same workflow with different inputs. Constant `input` is optional, must be valid JSON, and is limited by this integration to 8,192 UTF-8 bytes. Blank input sends the matched event. Input transformers are not exposed.

Standard and Express state machines receive asynchronous `StartExecution` calls. The state-machine definition and execution role remain separately configured; this connection does not change workflow states. Rule and workflow must be in the same region. The rule retains its existing event pattern or schedule.

Workflow actions must tolerate duplicate event delivery. Delivery retries, dead-letter handling, alarms, and permissions required by externally configured workflow encryption remain separate. The generated invocation role is distinct from the workflow execution role.

Tests cover native references, scoped invocation/trust policies, input validation, identifier conflicts, multiple targets, duplicate/order independence, and Terraform validation/dependency graphs for Standard and Express workflows. No live invocation is tested.
