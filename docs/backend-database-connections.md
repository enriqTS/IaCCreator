# Relational database IAM connections

Lambda and ECS support `authenticates_to` connections to RDS and Aurora. The required `database_user` selects an existing database user. The connection enables native IAM database authentication and grants only `rds-db:connect` on that user in that database. SQL privileges determine whether the user may read or write data; there is no IAM read/write selector.

RDS supports the `mysql`, `mariadb`, and `postgres` engines; Aurora supports `aurora-mysql` and `aurora-postgresql`. Unsupported or missing engines fail generation. A Terraform precondition also guards environment engine overrides. Engine-version, instance-class, and Region availability must be verified for the deployment.

The database module exports an IAM resource prefix using its actual ARN partition, Region, account, and immutable resource ID. RDS uses `resource_id`, Aurora uses `cluster_resource_id`; neither uses the editable database identifier. That prefix travels through a consumer module input, where the exact database username scopes the policy. This follows the [AWS IAM database policy model](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.IAMPolicy.html). Direct login assumes the runtime role belongs to the database account; cross-account role assumption is separate.

Consumer outputs `database_<database-node-name>_host`, `_port`, and `_region` expose connection metadata. Port is exported as a string. Use these values and the configured database user in application configuration. The application generates an IAM authentication token using its Lambda execution role or ECS task role and connects over TLS. The connection does not inject environment variables, retrieve secrets, generate tokens, or manage SQL users.

Create the database user with the engine's IAM authentication mechanism and assign SQL grants separately. For example, PostgreSQL users require the `rds_iam` role. VPC routing, subnets, security groups, and Aurora cluster instances are separate deployment prerequisites. See [AWS database authentication](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/database-authentication.html).

Both database service models expose `manage_master_user_password`, defaulting to false. Explicitly enabling it allows RDS to create and manage the master password in Secrets Manager; specify the master username as well. The application connection never enables that option or grants access to the master secret. For a newly created database, configure master-password management explicitly; an imported existing database can retain its existing credential ownership. The existing Aurora generator creates the cluster resource; provision its database instances separately before attempting application access.

Multiple users and consumers share database metadata outputs while retaining separately scoped IAM statements. Duplicate connections are idempotent and connection order does not change generated output.
