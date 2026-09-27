# EventBridge to Kinesis

Connect an EventBridge rule to Kinesis with `targets`. The rule module owns the target and a dedicated role, which trusts EventBridge for that rule ARN and permits `kinesis:PutRecord` only on the stream's native ARN. The target waits for its role policy; the stream module receives no reverse references.

`EventBridgeKinesisConfig` extends the shared target identifier and constant JSON input fields with optional `partition_key_path`. This integration accepts named fields in dot notation, for example `$.detail.customerId`, with a maximum length of 256 characters. Wildcards, recursive descent, and bracket notation are not exposed. The selected field must exist in the original event and resolve to a valid Kinesis partition key at runtime. Omitting or clearing the path leaves the Kinesis block absent, so EventBridge uses the event ID. See [AWS partition-key parameters](https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_KinesisParameters.html).

The optional constant JSON input changes the delivered record body; the partition path still refers to the original event. Input transformers are not exposed. Target identifiers must uniquely select a destination and all settings within a rule, including partition-key configuration. Identical duplicates are idempotent; distinct identifiers can send to the same stream with different partition settings.

The connection requires the same region. Configure stream capacity, consumers, delivery retries, dead-letter handling, and monitoring separately. Consumers must tolerate duplicate delivery, and partition-key choice can concentrate traffic in individual shards. Externally configured stream encryption needs its own key-policy and invocation-role permissions; the current stream model does not configure KMS encryption.

`EventBridgeKinesisHandler` extends the shared role-target handler through a typed config model and target-attribute hook. The Terraform `kinesis_target.partition_key_path` block follows the [provider target schema](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_target).

Tests cover scoped roles, native references, generated partition paths, validation boundaries, conflicting settings, multiple target IDs, duplicate/order independence, existing SNS/workflow regressions, and Terraform validation/dependency graphs. No live stream delivery is tested.
