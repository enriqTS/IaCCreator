# SQS to ECS polling

Connect SQS to ECS with `consumed_by` (the default for this pair). The typed empty connection config exposes no knobs; the backend registry supplies the editor schema. Queues and consumers must be in the same region under this integration.

The ECS task role receives `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:ChangeMessageVisibility`, and `sqs:GetQueueAttributes` for the connected queue ARN only. Batch deletion and visibility operations use the corresponding IAM actions. No send, purge, queue-management, or queue-list permissions are granted. See [SQS API permissions](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-api-permissions-reference.html).

The ECS module consumes native queue ARN/URL outputs and exports `sqs_<queue>_arn`, `sqs_<queue>_url`, and `sqs_<queue>_region` for application configuration. This connection does not inject container environment variables. Each queue has separate inputs, so multiple queues can feed one consumer without collisions or dependencies back from the queue module.

Application code must poll, process, acknowledge successful messages by deleting them, and extend visibility as needed. Configure long polling, retry/idempotency behavior, visibility timeouts, and network access separately. No event-source mapping, polling worker, dead-letter configuration, or autoscaling is generated. Standard and FIFO queues use the same access contract; the application remains responsible for their delivery semantics.

For a connected KMS key, the task role receives only `kms:Decrypt` on the native key ARN. External queue key identifiers are resolved with the existing KMS data lookup. Key policies must allow this identity, and old keys or keys used by a dead-letter queue's source messages may need additional grants. See [SQS consumer key permissions](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-key-management.html).

Tests cover exact permissions, both queue types, managed/external keys, task-role attachment, runtime outputs, multiple queues, duplicate connections, order independence, and Terraform validation/dependency graphs. They do not run a live consumer.
