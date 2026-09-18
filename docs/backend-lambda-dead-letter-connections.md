# Lambda dead-letter connections

Use `dead_letters_to` from Lambda to a standard SQS queue or standard SNS topic. The connection uses the typed empty config and is available through the connection-schema API. Existing `sends_to` and `publishes_to` relationships remain the defaults for their pairs.

The Lambda module receives the native destination ARN through `dead_letter_target_arn` and configures its function's `dead_letter_config`. Its execution role gets `sqs:SendMessage` or `sns:Publish` scoped to that ARN. The function already depends on its execution-role policy, so permissions are installed before the function configuration. Managed or external encryption keys use the existing KMS grant integration; their key policies must also permit the role.

A function can have one connected dead-letter destination. Conflicting destinations, a simultaneously configured external `dead_letter_target_arn`, and FIFO destinations are rejected. Duplicate identical connections are idempotent. A Terraform precondition rejects FIFO ARN overrides. These connections require the same region; destination modules do not receive references back to the function.

This captures discarded asynchronous events. It does not handle synchronous invocation errors or replace an SQS source queue's redrive policy. Lambda dead-letter delivery contains the original event and error attributes; invocation-record destinations are a separate feature. See [AWS Lambda dead-letter behavior and permissions](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async-retain-records.html#invocation-dlq).

Configure retry behavior, retention, SNS subscribers or SQS consumers, replay, and `DeadLetterErrors` alarms separately. Avoid sending failed events back into the same function. Destination size limits and key-policy permissions can prevent delivery. No event-invoke configuration, redrive policy, subscriber, or replay worker is created.

Tests cover both services, exact IAM scopes, managed keys, conflicts, FIFO rejection, existing default connections, duplicate/order independence, and Terraform validation/graphs with unencrypted, managed-key, and external-key destinations. No live failure delivery is tested.
