# DMS relational IAM endpoints

DMS supports `source_endpoint` (the default) and `target_endpoint` connections to RDS and Aurora. These four connection specifications create IAM-authenticated `aws_dms_endpoint` resources in the replication instance module and export their endpoint ARNs. Replication tasks, table mappings, and task settings remain separate.

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

Treat these as full-load endpoint configuration until CDC support and prerequisites have been verified for the selected engine pair. Binary logging or replication slots, source privileges, target schema preparation, and migration task configuration are separate. See the AWS [MySQL source](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.MySQL.html), [PostgreSQL source](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.PostgreSQL.html), [MySQL target](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.MySQL.html), and [PostgreSQL target](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.PostgreSQL.html) prerequisites.

Tests cover scoped grants, engine-specific settings, configuration rejection, identifier normalization and conflicts, deterministic aggregation, and generated Terraform validation and dependency graphs. They do not perform live endpoint connectivity or migration operations.
