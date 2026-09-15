# DocumentDB IAM client connections

Lambda and ECS support `authenticates_to` connections to DocumentDB. The connection exports client settings and the application's generated IAM role ARN. It has no password or read/write selector: DocumentDB database roles control authorization independently of IAM policies.

Set the DocumentDB node's `engine_version` to `5.0` explicitly. The integration currently supports that documented instance-based cluster version only. Generation rejects other or omitted versions; Terraform preconditions also reject incompatible variable overrides, and a postcondition checks the cluster's reported version. Connections do not select or upgrade an engine automatically.

The consumer module exports `documentdb_<cluster-node-name>_iam_client` with `host`, `reader_host`, string `port`, `role_arn`, `auth_mechanism`, `auth_source`, `tls`, `replica_set`, and `retry_writes`. Cluster endpoints and port travel through module outputs and inputs; the role ARN references the consumer's own role. ECS attaches that role to the task definition even when the connection contributes no IAM statements. Lambda already uses its generated execution role. Existing role policies are preserved.

Before application access works, a database administrator must create a user in `$external` named exactly after the exported IAM role ARN, enable `MONGODB-AWS` for that user, and assign the required database roles. This connection does not execute database commands or verify that mapping. No additional IAM data-access actions, credentials, or tokens are generated. See [AWS DocumentDB IAM identity authentication](https://docs.aws.amazon.com/documentdb/latest/devguide/iam-identity-auth.html).

Configure the application's compatible MongoDB driver to use its runtime AWS credential chain, `MONGODB-AWS`, `$external`, TLS with certificate verification and the AWS CA bundle, replica set `rs0`, and disabled retryable writes. The exported values are configuration metadata, not injected environment variables or packaged application code. Supplying a reader endpoint does not restrict database permissions.

Cluster instances, routing, security groups, database-user provisioning, and administrator credentials remain separate prerequisites. The current DocumentDB generator creates the cluster resource but does not model its master password or secret management; complete that credential configuration in the generated Terraform before creating a new cluster. The application connection never reuses or reads the administrator password. Terraform validation checks structure and dependency graphs, not deployment readiness or successful database login.

Multiple consumers can bind to one cluster with distinct runtime identities; one consumer can bind to several clusters. Repeated and reordered connections produce the same Terraform without cross-module dependency cycles. IAM role mappings and grants must be provisioned in each database separately.
