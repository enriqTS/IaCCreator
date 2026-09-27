# EventBridge to SNS

Connect EventBridge to a standard SNS topic with `targets`. The rule module owns the target and a dedicated role. The role trusts EventBridge only for the selected rule ARN and allows `sns:Publish` on the topic's native ARN. The target waits for its role policy. AWS supports this role-based target authorization as an alternative to topic policies; see [EventBridge target permissions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html).

This connection creates no SNS topic policy and therefore does not compete with existing policy owners such as S3 notifications. Any explicit topic-policy deny still applies. FIFO topics are rejected, with a Terraform precondition also rejecting FIFO ARN overrides. Rule and topic must share a region.

`EventBridgeInvocationConfig` supplies optional `target_id` and constant JSON `input` for SNS and Step Functions. Input is limited to 8,192 UTF-8 bytes and replaces the matched event; omit it to deliver the event. Target identifiers must uniquely select a destination and input within the rule. Exact duplicates are idempotent. Input transformers and FIFO message-group settings are not exposed.

`EventBridgeRoleTargetHandler` shares role, target, and identifier validation across the SNS and workflow implementations. Managed topic keys add key-scoped decrypt/data-key permissions to the publish role. External key identifiers use a KMS lookup; the external key policy must allow this role. The existing KMS grant helper supplies these references without creating an unrelated EventBridge execution role or changing SNS policies.

Configure subscriptions, delivery retries, dead-letter handling, and monitoring separately. Consumers must handle duplicate delivery. Tests cover permission scopes, managed/external keys, FIFO rejection, cross-service identifier conflicts, duplicate/order independence, workflow regressions, and Terraform validation/dependency graphs. No live publish is tested.
