# Step Functions to SQS queues

Connect a Step Functions workflow to a generated SQS queue with `sends_message`. Select an existing top-level JSONPath Pass state with `state_name` (default `Pass`). The connection replaces it with an `sqs:sendMessage` Task, preserving transitions and data paths while removing placeholder Result values. By default it sends the JSON-encoded state input; `message` supplies constant text instead. The SendMessage response becomes the state's result unless `ResultPath` discards or redirects it.

For a FIFO queue, set a queue name ending in `.fifo` and supply `message_group_id`. The task uses a supplied `message_deduplication_id` if present. Otherwise it relies on content-based deduplication when enabled, or generates a UUID per send. A fixed ID can suppress later messages with the same ID during SQS's deduplication window; a generated UUID does not deduplicate retries. FIFO settings on standard queues are rejected.

The workflow's external execution role must trust `states.amazonaws.com`. A workflow-owned inline policy grants `sqs:SendMessage` on the selected queue ARNs; Task parameters use the generated queue URLs. If a queue uses a connected KMS key or an external key identifier, the policy also grants `kms:Decrypt` and `kms:GenerateDataKey` on that key. External key identifiers resolve to ARNs through a KMS data source. The key policy must also permit the workflow role. Configure consumers, visibility timeouts, redrive, and failure handling separately.

SQS tasks compose with Secrets Manager, Lambda, ECS, Batch, and SNS tasks on distinct placeholders; overlapping bindings are rejected. Terraform preconditions recheck placeholders when the workflow definition is overridden by environment variables.

AWS documents the [Step Functions SQS SendMessage integration](https://docs.aws.amazon.com/step-functions/latest/dg/connect-sqs.html), [FIFO message identifiers](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-fifo-queue-message-identifiers.html), and [encrypted-queue producer permissions](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-key-management.html).
