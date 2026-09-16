# DMS relational IAM endpoints

DMS supports `source_endpoint` (the default) and `target_endpoint` connections to RDS and Aurora. These four connection specifications create IAM-authenticated `aws_dms_endpoint` resources in the replication instance module and export their endpoint ARNs. Add a separate `replication_task` connection to configure a stopped full-load migration using these endpoints.

Select a DMS replication engine version of **3.6.1 or newer** explicitly. Supported database engines are RDS MySQL, MariaDB, and PostgreSQL, and Aurora MySQL and PostgreSQL. Generation rejects incompatible engines and older or unspecified DMS versions. Terraform checks also guard engine/version overrides. AWS availability and database version/instance support must be verified for the deployment. See [DMS IAM endpoint requirements](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Endpoints.Creating.IAMRDS.html).

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

These connections do not create or read passwords, secret values, database users, or SQL grants. Managed database credentials are not automatically usable as DMS endpoint secrets: DMS secrets need host and port, and Aurora-managed master secrets omit those fields. Secrets Manager endpoint authentication and additional database engines remain follow-up work. See [DMS Secrets Manager requirements](https://docs.aws.amazon.com/dms/latest/userguide/security_iam_secretsmanager.html).

Treat these as full-load endpoint configuration until CDC support and prerequisites have been verified for the selected engine pair. Binary logging or replication slots, source privileges, target schema preparation, and CDC task configuration are separate. See the AWS [MySQL source](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.MySQL.html), [PostgreSQL source](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.PostgreSQL.html), [MySQL target](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.MySQL.html), and [PostgreSQL target](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.PostgreSQL.html) prerequisites.

Tests cover scoped grants, engine-specific settings, configuration rejection, identifier normalization and conflicts, deterministic aggregation, and generated Terraform validation and dependency graphs. They do not perform live endpoint connectivity or migration operations.

## Full-load replication tasks

A DMS → RDS/Aurora `replication_task` connection selects a managed source endpoint and a managed target endpoint on the same DMS instance. The target endpoint must connect to the database selected by the task connection. Both endpoint connections must exist in the diagram; generation rejects missing or mismatched references and rejects copying a database back into itself.

| Field | Meaning |
| --- | --- |
| `task_id` | Project-wide unique task identifier, normalized to lowercase |
| `source_endpoint_id` | Identifier on a `source_endpoint` connection from this DMS instance |
| `target_endpoint_id` | Identifier on a `target_endpoint` connection to the task's target database |
| `table_schema` | Explicit source schema name |
| `table_names` | Comma-separated list of 1–100 explicit table names |

All fields are required. Schema and table names support ASCII letters, digits, and underscores, with a letter or underscore first and a maximum of 63 characters. The backend trims, deduplicates, and sorts table names while preserving case. Each name becomes a numbered `explicit` selection rule for a table in the selected schema. Wildcards, views, filters, transformations, and arbitrary task-settings JSON are outside this initial integration. Selection semantics follow [AWS DMS selection rules](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Selections.html).

The generated `aws_dms_replication_task` uses native Terraform references to the replication instance and both endpoint ARNs. Its ARN is exported from the DMS module. Multiple tasks may share endpoints using distinct task IDs; identical duplicate connections and reordered table lists produce identical projects. Renaming a referenced endpoint identifier requires updating the task selector; resource node renames remain resolved by the connection's stable node IDs.

Tasks use `migration_type = "full-load"`, `start_replication_task = false`, and `FullLoadSettings.TargetTablePrepMode = "DO_NOTHING"`. Generation and deployment do not start a migration or request dropping/truncating existing tables. Deploy the replication instance and endpoint connections first, prepare compatible target schemas and empty tables, grant the required SQL permissions, and run successful endpoint connection tests. Then add the task connection, apply the generated task, and start it separately. Endpoint testing is not automated by Terraform. This staged deployment follows the [AWS scripted migration workflow](https://aws.amazon.com/blogs/database/automate-creation-of-multiple-aws-dms-endpoints-and-replication-tasks-using-the-aws-cli/). Schema conversion, mapping to different target schema/table names, CDC, and task logging configuration remain follow-up work. See [AWS full-load settings](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TaskSettings.FullLoad.html).

Terraform continues to manage the task's stopped state: a later apply can stop a task that was started externally. Review that lifecycle before operating a migration. See the [provider task resource](https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs/r/dms_replication_task.html.markdown). Terraform validation and dependency-graph tests verify generated projects, not live database connectivity or migration results.
