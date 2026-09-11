# KMS connection integration

The shared integration covers the thirteen registered `encrypts` targets and their currently registered runtime consumers and service publishers. Future relationships (for example Backup selections or Bedrock connections) must extend these rules when they are registered; an unrelated execution role is never granted access merely because it shares an architecture with a key.

## Native references and permissions

| Encrypted resource | Generated KMS behavior |
|---|---|
| S3 | Enables `aws:kms` bucket encryption without downgrading an existing `aws:kms:dsse` selection. Connected Lambda/ECS object readers receive Decrypt; writers receive GenerateDataKey and Decrypt for multipart upload support. |
| DynamoDB | Enables server-side encryption. DynamoDB manages its KMS grants; ordinary table/stream consumers do not receive unnecessary decrypt permissions. |
| SNS | Supplies the topic key. Connected Lambda publishers receive Decrypt and GenerateDataKey*. SNS delivery to a Lambda does not require that Lambda to decrypt the topic. |
| SQS | Supplies the queue key. Lambda publishers receive GenerateDataKey and Decrypt; Lambda event-source consumers receive only Decrypt. SNS and EventBridge delivery add service-principal permissions to the queue's managed key policy. |
| CloudWatch Logs | Supplies a policy-ready key. The regional Logs principal receives encryption operations constrained by the exact connected log-group ARN encryption contexts. Connected Lambda log writers receive key-scoped encryption permissions. |
| EBS / EFS | Forces encryption on and supplies the key. AWS manages the storage encryption grants; there is no grant to an unrelated application role. |
| Backup | Supplies the vault key. Vault provisioning and AWS-managed grant requirements belong to the deployment principal; backup selections and their service roles are a separate future relationship. |
| Secrets Manager | Supplies the secret key. Existing runtime-read and native-injection handlers grant scoped Decrypt to each actual consuming role. |
| DataZone / CodeArtifact | Supplies the domain key. The AWS service establishes its grants during provisioning, authorized by the deployment principal; no broad wildcard application-role access is generated. |
| Lambda | Supplies the environment-encryption key and grants the function role Decrypt/DescribeKey. |
| CloudTrail | Grants GenerateDataKey* and DescribeKey to CloudTrail, scoped to the connected trail identities; this does not grant log-reader access. |

The Terraform deployment identity must have the service-required KMS provisioning permissions, such as DescribeKey/CreateGrant, in addition to permissions to create the service itself. The generated default account-administrator key-policy statement delegates authorization to account IAM policies; it does not silently expand the Terraform caller's IAM permissions. For grant-based services, retain their AWS-managed grants rather than installing a second, conflicting grant manager in Terraform.

## Policy ownership and dependency graph

`kms_references.py` defines native key inputs and rejects more than one managed key for a resource. Duplicate identical connections are accepted. Explicit external key identifiers remain available when no managed key is connected.

`kms_policy_rules.py` contains focused service-policy rules. `kms_service_policy.py` combines them into exactly one `aws_kms_key_policy.services` in the key module, preserving the account administrator statement. All services sharing a key participate in the same policy, independent of connector order.

CloudTrail, Logs, and SNS source identities are exported from configured names plus partition, Region, and account data sources, independently of resource creation. The policy never depends on the encrypted resource's creation ARN. Native inputs use `service_key_arn`, which depends on policy installation, when a policy is needed; the previous `cloudtrail_key_arn` output remains available. This permits a single key to encrypt a topic, its destination queue, a consuming Lambda, its log group, and CloudTrail without a Terraform cycle.

SNS and EventBridge also share one queue-owned `aws_sqs_queue_policy.delivery`, with separate source-scoped statements, rather than overwriting each other's queue permissions. Subscriptions wait for that queue policy. EventBridge owns its target resource; queue policy source ARNs refer to independently created topic/rule outputs, preserving an acyclic graph.

CloudTrail statements have SourceArn and encryption-context conditions. Logs statements have exact log-group encryption contexts. SNS queue-delivery statements have exact source-topic ARN conditions. EventBridge queue delivery follows AWS's documented service-principal key-policy statement without source conditions; its permission is bounded to that individual key. Use a dedicated key where stronger separation from other EventBridge publishers is required. `Resource: "*"` inside a KMS key policy means the policy's own key, not every key in the account; runtime IAM grants always name a specific key ARN.

## Runtime IAM and external keys

`kms_consumer.py` derives grants from concrete data-plane actions rather than granting all KMS operations to every connected role. Managed keys cross module boundaries as outputs/inputs. External key IDs and aliases resolve through `data.aws_kms_key`, so IAM resources contain key ARNs rather than aliases. No secret values or key material are read into Terraform.

Execution-role policy files use `templatefile` with explicit interpolation contexts. Cross-module service ARNs become module inputs before rendering; literal `${var...}` placeholders must never reach IAM. Repeated grants and identical resource contributions are deduplicated, and variable/output ordering is deterministic. Lambda and its SQS event-source mapping wait for the execution policy. ECS application-access connections attach the generated role as the task role; native secret injection continues to use the execution role.

Lambda logging now uses the actual connected CloudWatch log group, including its KMS configuration, rather than creating a second unencrypted group inside the Lambda module. A Lambda may select only one log group. Terraform creates that group, so the connection grants stream creation and event writes rather than group creation.

External keys remain externally owned. Known AWS-managed key aliases are rejected for SNS/EventBridge delivery to encrypted queues, since their policies cannot authorize these publishers; a managed diagram key overrides that external fallback. SNS/EventBridge delivery and Lambda-to-Logs previews warn that the external key owner must supply the corresponding service-policy permissions. Cross-account external keys also require authorization in that external key policy. Existing ciphertext encrypted under older keys or object-specific keys cannot be inferred from a resource's current default key and requires separately maintained permissions.

## Existing generated projects

A moved block migrates the previous `aws_kms_key_policy.cloudtrail` address to the shared `services` policy. Queue-policy consolidation changes Terraform resource addresses across modules; for an already deployed project, retain one existing queue-policy state entry at the new `aws_sqs_queue_policy.delivery` address and remove obsolete duplicate state entries before applying. Review the plan rather than allowing old policy resources to delete permissions after the new policy is installed. Lambda logging no longer declares the old duplicate Lambda-owned log group; retain/export historical logs or migrate its state deliberately before applying a generated update.

## Verification

`tests/test_kms_access_integration.py` covers action-specific grants, managed/external keys, service-policy sharing, duplicate and reordered connectors, every native target's conflicting-key rejection, storage-encryption flags, ECS task credentials, and Terraform validation/plan graphs. Existing native-key, CloudTrail, and secret-consumer tests remain in place. `tests/test_iam_template_references.py` evaluates policy interpolation using Terraform console.

AWS references used to confirm the integration semantics:

- [SQS key management](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-key-management.html)
- [SNS key management](https://docs.aws.amazon.com/sns/latest/dg/sns-key-management.html)
- [CloudWatch Logs KMS encryption](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html)
- [EventBridge target permissions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-targets.html)
- [DataZone encryption at rest](https://docs.aws.amazon.com/datazone/latest/userguide/encryption-rest-datazone.html)
- [CodeArtifact domains and encryption](https://docs.aws.amazon.com/codeartifact/latest/ug/domain-overview.html)

S3 notification delivery to managed SNS/SQS destinations contributes the S3 service principal's `kms:GenerateDataKey` and `kms:Decrypt` permissions to the existing key-owned policy. A shared SNS/SQS key receives this statement once. As in the [AWS S3 documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/grant-destinations-permissions-to-s3.html), the KMS service grant applies to that key without a source-ARN condition; destination resource policies separately constrain publishing to connected bucket ARNs. External customer-managed key policies must be prepared by their owner, and AWS-managed key aliases are rejected for these relationships.
