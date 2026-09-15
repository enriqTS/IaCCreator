# Standalone ElastiCache client connections

Lambda and ECS support `connects_to` connections to the current ElastiCache node. That node provisions `aws_elasticache_cluster`: a Memcached cluster or a standalone Redis node. It does not provision a Valkey/Redis replication group or a serverless cache. The typed empty connection config has no IAM permission or credential selector.

Set the cache engine explicitly to `memcached` or `redis`, supply a node type and a compatible existing parameter group, and select a node count. Redis requires exactly one node; Memcached accepts 1–40 nodes in this integration. Generation rejects incomplete or incompatible settings, and a Terraform precondition guards the engine/count combination when variables are overridden. The optional `engine_version` field pins a version; AWS availability and parameter-group compatibility must be checked for the chosen deployment.

The service also exposes `subnet_group_name` and `security_group_ids` for existing VPC resources. Their values are preserved. The connection does not create subnet groups, security-group rules, routes, or private connectivity. These remain deployment prerequisites.

The consumer module exports `elasticache_<cache-node-name>_client` containing:

| Field | Meaning |
| --- | --- |
| `engine` | Native cache engine |
| `nodes` | List of objects with `address` and numeric `port`, ordered by native node ID |
| `tls` | Native `transit_encryption_enabled` value, with an unset value treated as false |
| `configuration_endpoint` | Memcached Auto Discovery endpoint; empty for Redis |

Values cross module boundaries through typed inputs, including `list(object({ address = string, port = number }))` and `bool`. No hostnames or ports are hardcoded. Memcached nodes contain separate cached data; clients must distribute keys across nodes rather than treat them as replicas. An Auto Discovery-capable client can use the configuration endpoint. Clients using a static node list must refresh it after scaling. These Terraform outputs are not automatically injected into application configuration. See [AWS Memcached Auto Discovery](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/AutoDiscovery.html).

The existing standalone generator does **not enable TLS or configure client authentication**. This connection reports the native transport setting rather than claiming the connection is encrypted. It adds no IAM data-access permissions, users, passwords, or tokens. Secure network access separately; exporting an endpoint does not authorize a client or limit commands and keys.

TLS provisioning and IAM login remain follow-up work. Memcached supports TLS under its engine/node/VPC constraints. Valkey/Redis IAM authentication requires a suitable replication group or serverless cache, TLS, and an IAM-enabled cache user with matching grants; those resource types are not represented by the current node. No implicit resource migration or replacement is performed. See [AWS TLS constraints](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/in-transit-encryption.html) and [AWS ElastiCache IAM authentication](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/auth-iam.html).

Multiple clients share cache outputs, and one client can bind to several caches. Duplicate and reordered connections produce identical projects. Tests evaluate endpoint projections and engine-specific discovery behavior using Terraform, preserve native numeric ports and TLS values, and validate generated projects and dependency graphs. They do not verify live cache reachability or perform data operations.
