# Backend Models

Data models in `app/models/` define the Pydantic schemas for API input validation, internal representation (IR), and diagram state.

## Input Models (`app/models/input_models.py`)

These are the Pydantic schemas for incoming API requests (Terraform generation).

### `ServiceType` (Enum)

Supported AWS service types. The enum covers 150+ services organized into categories:

**Core services (with full generators):** `lambda`, `s3`, `api-gateway`, `dynamodb`, `iam`, `cloudwatch`, `sns`, `sqs`

**Compute (full generators):** `ec2`, `ecs`, `eks`, `elastic-beanstalk`, `app-runner`, `batch`, `ec2-image-builder`, `lightsail`, `ecr`

**Analytics (full generators):** `athena`, `cloudsearch`, `emr`, `glue`, `kinesis`, `kinesis-firehose`, `msk`, `opensearch`, `redshift`

**Business Applications (full generators):** `connect`, `ses`, `pinpoint`

**Database (full generators):** `aurora`, `documentdb`, `elasticache`, `neptune`, `rds`, `timestream`

**Developer Tools (full generators):** `codebuild`, `codecommit`, `codedeploy`, `codepipeline`

**Other (full generators):** `appstream`, `amplify`, `gamelift`

**Icon-only services:** 80+ additional service types that appear in the diagram editor but do not have Terraform generators (e.g., `fargate`, `quicksight`, `lake-formation`, `managed-blockchain`).

### `ResourceConfig`

Service-specific configuration fields (all optional, used per service type):

| Field              | Type          | Used by      |
|--------------------|---------------|--------------|
| `handler`          | `str`         | Lambda       |
| `runtime`          | `str`         | Lambda       |
| `memory_size`      | `int`         | Lambda       |
| `timeout`          | `int`         | Lambda       |
| `is_layer`         | `bool`        | Lambda       |
| `description`      | `str`         | Lambda       |
| `environment_variables` | `dict`   | Lambda       |
| `tags`             | `dict`        | Lambda, S3, DynamoDB |
| `layers`           | `list[str]`   | Lambda       |
| `architectures`    | `str`         | Lambda       |
| `ephemeral_storage_size` | `int`   | Lambda       |
| `reserved_concurrent_executions` | `int` | Lambda |
| `publish`          | `bool`        | Lambda       |
| `versioning`       | `bool`        | S3           |
| `force_destroy`    | `bool`        | S3           |
| `object_lock_enabled` | `bool`     | S3           |
| `acceleration_status` | `str`      | S3           |
| `billing_mode`     | `str`         | DynamoDB     |
| `hash_key`         | `str`         | DynamoDB     |
| `hash_key_type`    | `str`         | DynamoDB     |
| `range_key`        | `str`         | DynamoDB     |
| `range_key_type`   | `str`         | DynamoDB     |
| `read_capacity`    | `int`         | DynamoDB     |
| `write_capacity`   | `int`         | DynamoDB     |
| `protocol_type`    | `str`         | API Gateway  |
| `cors_configuration` | `dict`      | API Gateway  |
| `routes`           | `list[dict]`  | API Gateway  |
| `stages`           | `list[dict]`  | API Gateway  |
| `authorizers`      | `list[dict]`  | API Gateway  |
| `retention_in_days`| `int`         | CloudWatch   |
| `kms_key_id`       | `str`         | CloudWatch   |
| `display_name`     | `str`         | SNS          |
| `fifo_topic`       | `bool`        | SNS          |
| `fifo_queue`       | `bool`        | SQS          |
| `visibility_timeout_seconds` | `int` | SQS       |
| `message_retention_seconds` | `int`  | SQS        |
| `instance_type`    | `str`         | EC2          |
| `ami`              | `str`         | EC2          |
| `ecs_launch_type`  | `str`         | ECS          |
| `eks_version`      | `str`         | EKS          |
| `rds_engine`       | `str`         | RDS          |
| `rds_instance_class` | `str`       | RDS          |

(Plus 30+ additional fields for other service types — see source for full list.)

### `ResourceInstance`

A named resource with `name`, `service_type`, `config`, and `terraform_variables` (dict of user-defined variable overrides). Includes a model validator that requires `hash_key` for DynamoDB resources.

### `Connection`

A connection between two resources: `source`, `target`, `connection_type` (e.g., `triggers`, `reads_from`, `writes_to`), and `connection_config` (optional dict for integration-specific settings like `batch_size`, `vpc_link_name`, `route_path`).

### `EnvironmentConfig`

An environment with `name` and `variables` (dict of string key-value pairs).

### `GlobalTerraformConfig`

Project-level Terraform configuration:
- `backend_type` (default `"local"`), `backend_config` (dict)
- `provider_region` (default `"us-east-1"`), `provider_profile` (optional)
- `terraform_version` (optional), `aws_provider_version` (optional)

### `ArchitectureDescription`

Top-level input schema: `project_name`, `environments` (min 1), `resources` (min 1), `connections` (optional), `global_terraform_config` (optional, defaults to `GlobalTerraformConfig()`).

## IR Models (`app/models/ir_models.py`)

Internal representation models used between the IR builder and code generators.

### `FileTree`

Type alias: `dict[str, str]` — maps relative file paths to file contents.

### `IAMStatement`

A single IAM policy statement: `effect` (default `"Allow"`), `actions` (list of strings), `resources` (list of Terraform references).

### `ConnectionIR`

Normalized connection: `source_name`, `target_name`, `source_service`, `target_service`, `connection_type`, `connection_config` (dict for integration-specific settings).

### `ResourceInstanceIR`

Enriched resource instance: `name`, `service_type`, `config` (ResourceConfig), `iam_statements` (populated by IRBuilder from connections), `connections` (list of ConnectionIR), `terraform_variables` (dict of user-defined variable values).

### `ServiceModuleIR`

Groups all instances of a single service type: `service_type`, `instances`.

### `EnvironmentIR`

Environment with `name`, `variables`, and `module_refs` (list of ServiceType values this environment references).

### `GlobalTerraformConfigIR`

Project-level Terraform configuration in the IR: `backend_type`, `backend_config`, `provider_region`, `provider_profile`, `terraform_version`, `aws_provider_version`.

### `ProjectIR`

Top-level IR: `project_name`, `environments`, `modules`, `connections`, `global_config` (GlobalTerraformConfigIR).

### `GeneratedFile`

A single generated file: `path` (relative), `content` (HCL or JSON string).

### `GenerationSummary`

Summary statistics: `project_name`, `environment_count`, `module_count`, `resource_instance_count`, `iam_policy_count`.

## Diagram Models (`app/models/diagram_models.py`)

Pydantic schemas for diagram state validation (save/load endpoints).

### `DiagramStateInput`

Top-level diagram state: `version` (int), `projectName`, `environments` (list of `EnvironmentConfigInput`), `elements` (list of `SerializedElementInput`), `connectors` (list of `SerializedConnectorInput`), `viewport` (`ViewportInput`), `globalTerraformConfig` (optional dict).

### `SerializedElementInput`

Diagram element: `id`, `type`, `x`, `y`, `name`. Configured with `extra="allow"` for extensibility.

### `SerializedConnectorInput`

Diagram connector: `id`, `sourceId`, `targetId`, `type`. Configured with `extra="allow"`.

### `ViewportInput`

Viewport state: `x`, `y`, `zoom` (all floats).

### `EnvironmentConfigInput`

Environment: `name`, `variables` (dict, default empty).

## API Gateway Models (`app/models/api_gateway_models.py`)

Additional Pydantic models for enhanced API Gateway configuration (routes, stages, authorizers, custom domains, VPC links, integrations).
