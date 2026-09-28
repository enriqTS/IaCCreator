# Step Functions to SNS topics

Connect a Step Functions workflow to a generated SNS topic with `publishes`. Select an existing top-level JSONPath Pass state with `state_name` (default `Pass`). The connection replaces it with an `sns:publish` Task, preserving transitions and data paths while removing placeholder Result values. By default it publishes the JSON-encoded state input; `message` supplies constant text instead. The publish response becomes the state's result unless `ResultPath` discards or redirects it.

For a FIFO topic, set a topic name ending in `.fifo` and supply `message_group_id`. The task uses a supplied `message_deduplication_id` if present. Otherwise it relies on the topic's content-based deduplication when enabled, or generates a UUID per publish. A fixed ID can suppress later messages with the same ID during SNS's deduplication window; a generated UUID does not deduplicate retries. FIFO settings on standard topics are rejected.

The workflow's external execution role must trust `states.amazonaws.com`. A workflow-owned inline policy grants `sns:Publish` on the selected generated topics. If a topic uses a connected KMS key or an external key identifier, the policy also grants `kms:Decrypt` and `kms:GenerateDataKey*` on that key. External key identifiers resolve to ARNs through a KMS data source. The key policy must also permit the workflow role. Configure subscribers, delivery monitoring, and failure handling separately.

SNS tasks compose with Secrets Manager, Lambda, ECS, and Batch tasks on distinct placeholders; overlapping bindings are rejected. Terraform preconditions recheck placeholders when the workflow definition is overridden by environment variables.

AWS documents the [Step Functions SNS Publish integration](https://docs.aws.amazon.com/step-functions/latest/dg/connect-sns.html), [FIFO grouping](https://docs.aws.amazon.com/sns/latest/dg/fifo-message-grouping.html), [FIFO deduplication](https://docs.aws.amazon.com/sns/latest/dg/fifo-message-dedup.html), and [encrypted-topic publisher permissions](https://docs.aws.amazon.com/sns/latest/dg/sns-key-management.html).
