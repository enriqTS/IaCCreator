# ElastiCache Serverless IAM clients

The `elasticache-serverless` node provisions `aws_elasticache_serverless_cache` for Valkey (default) or Redis OSS. It is separate from the existing standalone `elasticache` node, so existing Redis/Memcached clusters retain their resource type. The editor includes the new node and discovers its connection schemas from the backend.

Service fields are `cache_name`, `engine`, optional `user_group_id`, `subnet_ids`, and `security_group_ids`. Subnet → cache `places` and Security Group → cache `associates` connections aggregate managed references alongside external IDs. Select compatible subnets/security groups in one VPC and configure routes and ingress separately. Empty placement lists leave placement selection to AWS. The generator exports cache ARN, primary endpoint, and reader endpoint. Capacity limits, snapshots, customer-managed encryption keys, and engine-version pinning are not exposed in this initial resource model. See the [provider resource](https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs/r/elasticache_serverless_cache.html.markdown).

Lambda and ECS support `authenticates_to` with a required `user_id`. The selected cache must specify an existing user group. Provision an IAM-authenticated cache user whose ID and user name are identical, add it to that group, and configure a suitable access string for allowed commands and keys. Verify authentication mode, membership, group/engine compatibility, and the group's other users before deployment; this integration does not query or enforce those external properties. The user group is attached to the cache through its native resource argument.

The connection grants only `elasticache:Connect`, scoped to the native cache ARN and the selected user ARN in the cache's partition, account, and Region. It uses the Lambda execution role or ECS task role. The selected user's database permissions remain controlled by its external access string. No users, user groups, passwords, tokens, or secret values are created or read. See [AWS ElastiCache IAM authentication](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/auth-iam.html).

Each cache/user binding exports client metadata from the consumer module:

| Field | Meaning |
| --- | --- |
| `cache_name` | Lowercase native name used when signing a token |
| `engine` | Native cache engine |
| `host`, `port` | Primary endpoint hostname and numeric port |
| `region` | Region derived from the native cache ARN |
| `user_id`, `user_name` | Selected external IAM user identity |
| `tls` | `true`; serverless caches use TLS |
| `resource_type` | `ServerlessCache`, required in the signing request |

Applications must use an appropriate cluster-aware TLS client, generate SigV4 tokens with runtime credentials, and pass `ResourceType=ServerlessCache` when signing. Tokens last 15 minutes; long-lived connections require a fresh token and reauthentication before the 12-hour connection limit. Outputs are not automatically injected into application configuration. Native version checks require Redis 7.0+ or Valkey 7.2+; Terraform guards engine and user-group overrides. See [AWS IAM client requirements](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/auth-iam.html) and [serverless TLS behavior](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/in-transit-encryption.html).

IAM connections require the consumer and cache to use the same Region. Multiple users and consumers share native cache outputs without duplicating the cache. Cross-module values travel through inputs and outputs; the cache does not depend on consumer resources. Tests cover grant scoping, invalid users and missing groups, ARN partition/account handling, native numeric ports, deterministic aggregation, and Terraform validation/dependency graphs. They do not verify live cache authentication or external user-group configuration. Node-based replication-group support remains separate follow-up work.
