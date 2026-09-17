# DMS relational endpoints

DMS supports `source_endpoint` (the default) and `target_endpoint` connections to RDS and Aurora. These four connection specifications create IAM-authenticated `aws_dms_endpoint` resources in the replication instance module and export their endpoint ARNs. Add a separate `replication_task` connection to configure a stopped migration using these endpoints.

For IAM endpoints, select a DMS replication engine version of **3.6.1 or newer** explicitly. Supported database engines are RDS MySQL, MariaDB, and PostgreSQL, and Aurora MySQL and PostgreSQL. Generation rejects incompatible engines and older or unspecified DMS versions. Terraform checks also guard engine/version overrides. AWS availability and database version/instance support must be verified for the deployment. See [DMS IAM endpoint requirements](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Endpoints.Creating.IAMRDS.html).

The typed connection configuration contains:

| Field | Meaning |
| --- | --- |
| `endpoint_id` | Project-wide unique DMS endpoint identifier, normalized to lowercase |
| `database_user` | Existing database user configured for IAM authentication |
| `database_name` | Existing database for the endpoint |
| `certificate_arn` | Database CA certificate already imported into DMS |

The certificate must be a DMS certificate ARN, not an ACM certificate ARN. A Terraform precondition checks its partition, account, and Region against the native replication instance ARN. Connections use `verify-ca` TLS, which verifies the certificate authority; it does not provide `verify-full` hostname verification. Certificate import and rotation are external prerequisites.

Each endpoint gets a dedicated DMS-trusted IAM role with `rds-db:connect` scoped to the database's immutable resource ID and the selected database user. The database generator enables native IAM authentication. Host, numeric port, engine, and IAM resource identity derive from the database's Terraform resource and cross module boundaries as outputs and inputs. All endpoint resources remain in the DMS module, avoiding reverse database dependencies. Identical connections deduplicate; conflicting endpoint identifiers are rejected across the project.

Provision the database user and its engine-specific IAM login and migration SQL permissions separately. The deployment identity needs permission to pass the endpoint role to DMS. Network paths, security-group rules, standard DMS account roles, database instances, and test-connection remain deployment responsibilities. Existing DMS Subnet and Security Group connections can supply placement, but do not establish database reachability by themselves.

These connections do not create or read passwords, secret values, database users, or SQL grants. Managed database credentials are not automatically usable as DMS endpoint secrets: DMS secrets need host and port, and Aurora-managed master secrets omit those fields. Additional database engines remain follow-up work. See [DMS Secrets Manager requirements](https://docs.aws.amazon.com/dms/latest/userguide/security_iam_secretsmanager.html).

IAM-authenticated PostgreSQL sources are restricted to full load; MySQL-compatible sources also support the CDC task modes described below. Source logging, SQL privileges, and target schema preparation remain deployment prerequisites. See the AWS [MySQL source](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.MySQL.html), [PostgreSQL source](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.PostgreSQL.html), [MySQL target](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.MySQL.html), and [PostgreSQL target](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.PostgreSQL.html) prerequisites.

Tests cover scoped grants, engine-specific settings, configuration rejection, identifier normalization and conflicts, deterministic aggregation, and generated Terraform validation and dependency graphs. They do not perform live endpoint connectivity or migration operations.

## Secrets Manager endpoints

Use `source_secret_endpoint` or `target_secret_endpoint` for RDS MySQL, MariaDB, PostgreSQL, SQL Server Enterprise/Standard, or Aurora MySQL/PostgreSQL. These four additional specifications use the same endpoint identifier, database name, and imported certificate fields. Instead of `database_user`, supply `secrets_manager_arn` (a full secret ARN) and `secrets_manager_access_role_arn` (an existing IAM role ARN). Secret endpoints do not enable database IAM authentication or impose the IAM-specific DMS 3.6.1 minimum.

Prepare a secret with `host`, `port`, `username`, and `password` matching the selected database. The generator does not read its contents, verify its database identity, or create credentials. It exports the native database engine for an override guard; host and port come exclusively from the secret. Terraform emits neither clear-text connection arguments nor secret-value data sources. Aurora-managed master secrets lack the required host/port fields and cannot be used directly.

The access role must trust DMS and allow `secretsmanager:GetSecretValue` on the selected secret, with customer-managed key permissions where required. Cross-account secrets additionally require the appropriate resource policy and `DescribeSecret` permission. The deployment identity needs `iam:GetRole`, `iam:PassRole`, and `secretsmanager:DescribeSecret`. Follow the [AWS secret and role setup instructions](https://docs.aws.amazon.com/dms/latest/userguide/security_iam_secretsmanager.html), including the applicable DMS service principal. Role setup, secret population/rotation, database SQL grants, network reachability, and live endpoint tests remain external prerequisites.

Endpoints use `verify-full` TLS for SQL Server and `verify-ca` for the other supported engines, with certificate account/Region checks. Identifiers are unique across both authentication methods. Tasks can combine IAM and secret endpoints; MySQL-family sources support the existing CDC modes, and PostgreSQL/SQL Server secret sources support the CDC modes below. Since external secret contents are not inspected, verify that they match diagram database identities before running a task.

## Replication tasks

A DMS → RDS/Aurora `replication_task` connection selects a managed source endpoint and a managed target endpoint on the same DMS instance. The target endpoint must connect to the database selected by the task connection. Both endpoint connections must exist in the diagram; generation rejects missing or mismatched references and rejects copying a database back into itself.

| Field | Meaning |
| --- | --- |
| `task_id` | Project-wide unique task identifier, normalized to lowercase |
| `source_endpoint_id` | Identifier on a `source_endpoint` or `source_secret_endpoint` connection from this DMS instance |
| `target_endpoint_id` | Identifier on a `target_endpoint` or `target_secret_endpoint` connection to the task's target database |
| `table_schema` | Explicit source schema name |
| `table_names` | Comma-separated list of 1–100 explicit table names |
| `target_schema` | Optional destination schema name |
| `target_table_prefix` | Optional prefix for all selected destination table names |
| `migration_type` | `full-load` (default), `full-load-and-cdc`, or `cdc` |
| `cdc_start_position` | Required native MySQL binlog position, PostgreSQL WAL LSN, or SQL Server LSN for CDC-only tasks |

The first five fields are required; destination naming fields may be omitted or left empty. CDC-only tasks also require a start position. Schema and table names support ASCII letters, digits, and underscores, with a letter or underscore first and a maximum of 63 characters. The backend trims, deduplicates, and sorts table names while preserving case. Each name becomes a numbered `explicit` selection rule for a table in the selected schema. Wildcard selection, views, filters, column transformations, and arbitrary task-settings JSON remain outside this integration. Selection semantics follow [AWS DMS selection rules](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Selections.html).

The generated `aws_dms_replication_task` uses native Terraform references to the replication instance and both endpoint ARNs. Its ARN is exported from the DMS module. Multiple tasks may share endpoints using distinct task IDs; identical duplicate connections and reordered table lists produce identical projects. Renaming a referenced endpoint identifier requires updating the task selector; resource node renames remain resolved by the connection's stable node IDs.

Tasks default to `migration_type = "full-load"` and always use `start_replication_task = false`. Full-load modes use `FullLoadSettings.TargetTablePrepMode = "DO_NOTHING"`; CDC-only tasks omit full-load settings. Generation and deployment do not start a migration or request dropping/truncating existing tables. Deploy the replication instance and endpoint connections first, prepare compatible target schemas and tables (empty for full load, snapshot-consistent for CDC-only), grant the required SQL permissions, and run successful endpoint connection tests. Then add the task connection, apply the generated task, and start it separately. Endpoint testing is not automated by Terraform. This staged deployment follows the [AWS scripted migration workflow](https://aws.amazon.com/blogs/database/automate-creation-of-multiple-aws-dms-endpoints-and-replication-tasks-using-the-aws-cli/). Schema conversion, individual table renames, and task logging configuration remain follow-up work. See [AWS full-load settings](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TaskSettings.FullLoad.html).

Terraform continues to manage the task's stopped state: a later apply can stop a task that was started externally. Review that lifecycle before operating a migration. See the [provider task resource](https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs/r/dms_replication_task.html.markdown). Terraform validation and dependency-graph tests verify generated projects, not live database connectivity or migration results.

## Destination naming

Set `target_schema` to rename the selected source schema in the destination, and `target_table_prefix` to add the same prefix to each selected table. For example, source `public.customers` with target schema `archive` and prefix `copy_` maps to `archive.copy_customers`. Both fields preserve case. Prefixes follow the same ASCII identifier convention, and every resulting table name must fit the integration's 63-character limit. Omitting these settings preserves the original mapping; choosing the original schema name emits no redundant rename rule.

Schema renaming uses one schema transformation and prefixing uses one table transformation. The prefix rule applies to tables already selected by the explicit selection rules; it does not include additional source tables. Generated rule IDs are unique and deterministic. The source and target must still be different databases, even when destination names differ.

Prepare destination schemas, tables, and SQL permissions for the transformed names before starting a task. These transformations change names rather than convert column types or database schemas. Changes to transformations on an existing task require a restart, not merely a resume. See [AWS DMS transformation rules](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Transformations.html).

## Ongoing replication (CDC)

`full-load-and-cdc` loads existing rows and then replicates ongoing changes. `cdc` replicates changes into an already prepared target. This integration permits both modes with IAM- or Secrets Manager-authenticated RDS MySQL, RDS MariaDB, and Aurora MySQL sources. PostgreSQL and Aurora PostgreSQL sources support CDC through Secrets Manager endpoints. Generation rejects PostgreSQL IAM sources for CDC, and Terraform preconditions guard source engine overrides. PostgreSQL and Aurora PostgreSQL remain supported as targets. AWS prohibits IAM authentication for PostgreSQL replication connections; see [RDS IAM limitations](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html).

CDC-only tasks require `cdc_start_position` in the source engine's native format: a MySQL binlog coordinate such as `mysql-bin-changelog.000024:373`, a PostgreSQL WAL LSN such as `4AF/B00000D0`, or a SQL Server LSN such as `00000014:00000061:0001`. PostgreSQL LSN components each contain 1–8 hexadecimal digits. The backend validates the format but cannot verify log availability or consistency with target data. Coordinate that position with the target's initial snapshot. It is rejected for both full-load modes; timestamp starts, DMS recovery checkpoints, and automatic start-position discovery are not exposed. The start point is fixed when DMS creates the task; use a new task ID when selecting another point. See [AWS CDC start points](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Task.CDC.html).

For MySQL sources, configure the prerequisites before deploying and testing endpoints: ROW binary logging, FULL row images, sufficient binlog retention and backup settings, and the required replication SQL privileges. Those database settings and grants are not provisioned by the connection. Verify version/topology support and table keys for reliable updates/deletes. See [MySQL-compatible source requirements](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.MySQL.html). Endpoint IAM database-login permission does not grant replication privileges inside the database.

Both CDC modes retain explicit table selection and optional destination naming transformations. Tasks remain stopped after deployment, and Terraform can stop externally started tasks on a later apply. CDC-only destinations need data consistent with the chosen position rather than empty tables. Bidirectional replication and loopback prevention are not configured. Tests validate generated Terraform and source restrictions without running a live migration.

## PostgreSQL logical replication

`source_secret_endpoint` exposes optional `postgres_plugin_name` (`test-decoding` or `pglogical`) and `postgres_slot_name` fields. They are rejected on MySQL sources and are absent from target/IAM endpoint schemas. PostgreSQL source endpoints render these values through `postgres_settings` and explicitly preserve DMS's enabled DDL capture when adding that block. Omitted slot/plugin fields retain DMS defaults.

For `full-load-and-cdc`, omit the slot name and let DMS create its slot when the task starts. A plugin can be selected explicitly or left to DMS. This integration reserves named slots for `cdc` tasks, which require an existing inactive slot and an explicit matching plugin on the source endpoint, plus a WAL LSN on the task. Slot names permit 1–63 lowercase letters, digits, or underscores. A named slot on the same diagram database cannot be assigned to multiple CDC tasks, including through different endpoints or replication instances. Identical task duplicates remain idempotent.

Prepare logical replication settings, sufficient WAL retention and replication capacity, database grants, and suitable table keys before migration. Check DDL-capture prerequisites and, for Aurora PostgreSQL, `synchronous_commit`. These settings and SQL objects are not provisioned by the generator. Follow [AWS PostgreSQL source setup](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.PostgreSQL.html).

Verify the secret's database identity, slot database/plugin, inactivity, retained WAL, and target snapshot consistency externally; Terraform does not inspect them. A slot cannot support concurrent consumers. Monitor disk usage from retained WAL and manage slot cleanup separately. See [native CDC start points](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Task.CDC.html). Tests validate configuration, generated Terraform, and dependency graphs; no live migration is performed.

## RDS SQL Server

RDS engines `sqlserver-ee` and `sqlserver-se` map to DMS `engine_name = "sqlserver"` through Secrets Manager source/target endpoints. SQL Server uses `verify-full`: the secret's host must match the database certificate, and the CA must be imported into DMS. Other supported engines retain `verify-ca`. See [DMS TLS compatibility](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Security.SSL.html).

SQL Server sources support stopped full-load, full-load-plus-CDC, and CDC-only tasks. SQL Server targets accept CDC from supported MySQL, PostgreSQL, and SQL Server sources. IAM endpoint authentication, Express/Web editions, and PostgreSQL slot/plugin fields are rejected. Connection specifications and fields are unchanged; select the SQL Server engine on the RDS node. Existing identifier restrictions and explicit table selection apply, including selecting the source schema (often `dbo`) and preparing destination schemas/tables.

Use SQL authentication in the external secret; Windows authentication is unsupported. Prepare source read/metadata permissions or target `db_owner` permissions as applicable, compatible database/DMS versions, instance sizing, network reachability, and certificate hostname matching. Schema conversion and SQL grants remain external. Review [SQL Server source requirements](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.SQLServer.html) and [target limitations](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.SQLServer.html), including identity/computed columns, BCP loading, and PostgreSQL boolean conversion. No live migration or data-conversion checks are performed by the generator.

### SQL Server ongoing replication

For RDS SQL Server source CDC, select DMS replication engine **3.5.3 or newer** explicitly. This integration requires that minimum to include transaction-log backup access, avoiding the older active-log-only limitation. Generation rejects older/missing versions, and a task precondition checks the native replication instance version after Terraform variable overrides. Full-load-only tasks and SQL Server targets do not acquire this requirement. See [AWS SQL Server source limitations and permissions](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.SQLServer.html).

CDC-only tasks require `cdc_start_position` as three hexadecimal components of 8, 8, and 4 digits separated by colons. Both hexadecimal cases are accepted and preserved. MySQL/PostgreSQL positions are rejected for SQL Server, and SQL Server LSNs are rejected for those engines. Full-load-plus-CDC omits an explicit position. Both modes retain `verify-full` TLS, secret references, explicit table mappings, destination naming transformations, and stopped task execution.

Enable MS-CDC on the RDS database and every selected table, including tables with primary keys. Prepare compatible SQL Server versions, retention, backups, capture/cleanup jobs, and the database/login permissions needed by DMS to read active and backup transaction logs. This generator does not execute setup SQL or enable automatic MS-CDC setup on the endpoint. Follow the [RDS/cloud SQL Server CDC setup](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.SQLServer.CDC.html#CHAP_Source.SQLServer.CDC.CloudSQLServer) and verify the selected LSN remains available and matches the target's initial data before starting.

Validate endpoint connectivity and log access externally. Review [RDS SQL Server log processing and tuning](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Troubleshooting_Latency_Source_SQLServer.html), including safeguard behavior and storage capacity. Database configuration, data consistency, and live replication are not verified by Terraform validation tests.
