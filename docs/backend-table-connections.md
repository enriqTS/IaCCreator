# Keyspaces and Timestream table connections

Lambda and ECS support `reads_from` and `writes_to` connections to Keyspaces and Timestream. Each connection requires an explicit `table_name`; read access is the default. Table names cannot contain IAM wildcard characters. The connected service module creates the keyspace or database, while the selected table must be provisioned separately in that container.

The shared `TableAccessHandler` exports a table ARN derived from the connected database/keyspace ARN, its name, and its Region. These values cross into the application module through inputs. Each consumer exports a `table_access_<hash>` object containing `table_arn`, `table_name`, `database_name`, and `region`. The stable hash identifies the database node and table name; read/write connections to the same table share metadata. Use these outputs to configure application code. They do not inject environment variables or credentials.

Application grants attach to the Lambda execution role or ECS task role. Multiple tables and read/write modes aggregate deterministically; repeated identical connections do not duplicate IAM statements. Network routing and endpoint policies remain separate. These connections do not provision tables, retrieve secrets, or grant database administration permissions. External table encryption configurations remain owned by the table/key owners.

## Keyspaces

Read access grants `cassandra:Select` on the exact table ARN; write access grants `cassandra:Modify`, which permits inserts, updates, and deletes. Both modes grant separate read-only system metadata access under the target account and Region's `/keyspace/system*` ARN. Cassandra drivers require these reads during initialization, including when application data access is write-only. This follows [AWS Keyspaces IAM requirements](https://docs.aws.amazon.com/keyspaces/latest/devguide/security_iam_service-with-iam.html).

Use a Cassandra driver with the AWS SigV4 authentication plugin and the workload's role credentials. Select the regional Keyspaces endpoint from the exported Region and connect over TLS on port 9142. `database_name` identifies the keyspace. No IAM user or service-specific username/password is created. Keyspace and table schema creation use separately managed deployment permissions.

## Timestream

These connections target Timestream for LiveAnalytics. Read access grants `timestream:Select` and `timestream:DescribeTable`; write access grants `timestream:WriteRecords` and `timestream:DescribeTable`. Each data grant is limited to the selected table ARN. Queries that read several tables require access connections for each table.

A separate `timestream:DescribeEndpoints` grant uses `Resource: "*"`, since AWS does not support resource-level permissions for this action. The SDK discovers endpoints in the exported Region. Query cancellation, table-independent queries, scheduled queries, unloads, and table administration are not included. See the [Timestream authorization reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazontimestream.html).

LiveAnalytics is closed to new customers as of June 20, 2025; eligible existing payer accounts can continue using it. These connections do not target Timestream for InfluxDB. See [AWS's availability notice](https://docs.aws.amazon.com/timestream/latest/developerguide/AmazonTimestreamForLiveAnalytics-availability-change.html).
