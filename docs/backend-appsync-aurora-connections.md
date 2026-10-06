# AppSync → Aurora PostgreSQL

The `resolves_with` connection binds a GraphQL field to an AppSync-owned relational data source backed by the Aurora PostgreSQL Data API. Set the Aurora node's `engine` to `aurora-postgresql`, choose an explicit `engine_version` supported by Data API in the deployment Region, and set `database_name`. Standalone RDS instance nodes and Aurora MySQL are not supported by this connection.

Connecting enables the cluster's HTTP Data API endpoint, encrypted storage, and an RDS-managed master password. It adds a private `db.serverless` writer with a 0.5–2 ACU capacity range; this instance incurs database cost even when unused. The managed master secret ARN is exported for administrator bootstrap. The AppSync role never receives access to that secret. Use it to create the table and a database user with only the required SQL privileges, then store that user's credentials in an existing Secrets Manager secret. Supply its ARN as `credential_secret_arn` on the connection. If that secret uses a customer-managed KMS key, supply the key ARN as `credential_kms_key_arn`; the key policy must also allow the generated role. Deploying the full project requires the credential secret to exist, so initial database/user bootstrap may require staging the cluster before applying the AppSync data source.

| Operation | Default GraphQL type | Arguments | Returned value |
|---|---|---|---|
| `get_row` | Query | `id` | One row or `null` |
| `list_rows` | Query | None | Up to 50 rows |
| `insert_row` | Mutation | `input` object | Inserted row |
| `update_row` | Mutation | `id`, `input` object | Updated row or `null` |
| `delete_row` | Mutation | `id` | Deleted row or `null` |

The connection requires an existing `table_name`, optionally qualified as `schema.table`. `id_column` defaults to `id`; `id_argument` and `input_argument` can rename the GraphQL arguments. The configured GraphQL field and return type must match the selected operation and table columns. Update removes the ID column from input values and rejects an update with no remaining columns. The generated resolver uses AppSync's PostgreSQL SQL helpers, which escape table/column identifiers and bind client values as query parameters. List results are capped at 50 without pagination. Each operation is one Data API statement; the connection does not create schemas or tables, manage migrations, or configure database-user SQL grants.

One data source and role serve all fields connected to the same Aurora node. They must share one database-user secret and optional KMS key. The role trusts AppSync only for the generated API ARN, grants `rds-data:ExecuteStatement` only on the cluster ARN, and grants `secretsmanager:GetSecretValue` only on the selected credential secret. The Aurora module's Data API ARN output waits for its writer instance, so the AppSync module is ordered after the usable cluster. A GraphQL field can have only one generated resolver across all AppSync data-source connections.

Data API support depends on the engine version and Region; check [AWS's availability table](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.regions.html) before deployment. The implementation follows the [AppSync Aurora resolver reference](https://docs.aws.amazon.com/appsync/latest/devguide/resolver-reference-rds-js.html), [AppSync data-source schema](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_datasource), and [Terraform Serverless v2 cluster example](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_cluster).
