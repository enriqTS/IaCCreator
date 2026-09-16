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

The standalone generator supports opt-in Memcached TLS through `transit_encryption_enabled`, which defaults to false. Client connections report the native transport setting. It adds no IAM data-access permissions, users, passwords, or tokens. Secure network access separately; exporting an endpoint does not authorize a client or limit commands and keys.

Redis/Valkey TLS provisioning and IAM login remain follow-up work. Memcached TLS prerequisites are described below. Valkey/Redis IAM authentication requires a suitable replication group or serverless cache, TLS, and an IAM-enabled cache user with matching grants; those resource types are not represented by the current node. The generator does not switch the cluster to a different resource type. See [AWS TLS constraints](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/in-transit-encryption.html) and [AWS ElastiCache IAM authentication](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/auth-iam.html).

Multiple clients share cache outputs, and one client can bind to several caches. Duplicate and reordered connections produce identical projects. Tests evaluate endpoint projections and engine-specific discovery behavior using Terraform, preserve native numeric ports and TLS values, and validate generated projects and dependency graphs. They do not verify live cache reachability or perform data operations.

## Memcached TLS provisioning

Enable `transit_encryption_enabled` explicitly on a Memcached cluster, select engine version 1.6.12 or newer, supply an existing VPC `subnet_group_name`, and choose a supported node type. M1, M2, M3, R3, and T2 node families are rejected. AWS Region availability and parameter-group compatibility remain deployment checks. Redis on the standalone cluster resource is rejected when TLS is requested; use a suitable replication-group resource for Redis TLS.

Backend validation rejects incomplete TLS configurations, and generated Terraform preconditions guard engine/version, node-family, and subnet-group overrides. The native `transit_encryption_enabled` argument is emitted only for an enabled configuration. Leaving TLS disabled preserves the previous generated resource arguments. TLS provisioning also works without a client connection.

Memcached TLS is selected at creation and cannot be toggled on an existing cluster. Changing it requires cluster replacement; review the Terraform plan and arrange cache warm-up and client cutover. Use TLS-capable clients with certificate and hostname verification for both node connections and Auto Discovery. TLS does not add IAM authentication, users, or credentials. The existing native `tls` output continues to describe the deployed cache. See [AWS Memcached TLS constraints](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/in-transit-encryption.html).
