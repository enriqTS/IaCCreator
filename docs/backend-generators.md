# Backend Generators

The `app/generators/` package contains HCL/Terraform code generators for each AWS service type, a shared HCL renderer, an IAM policy generator, a tfvars generator, a global config generator, variable schemas, and a registry that maps service types to generator instances.

## Generator Protocol (`app/generators/base.py`)

`ServiceGenerator` is a Python `Protocol` that every service generator must implement:

```python
class ServiceGenerator(Protocol):
    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str: ...
    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str: ...
    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str: ...
```

Each method returns a string of valid HCL content for the corresponding `.tf` file.

## Generator Registry (`app/generators/registry.py`)

`GENERATOR_REGISTRY` is a `dict[ServiceType, ServiceGenerator]` mapping each service type to a singleton generator instance. Used by `FileTreeAssembler` to look up the correct generator when producing per-instance files.

### Core Services

| ServiceType    | Generator Class        |
|----------------|------------------------|
| `lambda`       | `LambdaGenerator`      |
| `s3`           | `S3Generator`          |
| `dynamodb`     | `DynamoDBGenerator`    |
| `api-gateway`  | `APIGatewayGenerator`  |
| `cloudwatch`   | `CloudWatchGenerator`  |
| `iam`          | `IAMGenerator`         |
| `sns`          | `SNSGenerator`         |
| `sqs`          | `SQSGenerator`         |

### Compute Services

| ServiceType          | Generator Class              |
|----------------------|------------------------------|
| `ec2`               | `EC2Generator`               |
| `ecs`               | `ECSGenerator`               |
| `eks`               | `EKSGenerator`               |
| `elastic-beanstalk` | `ElasticBeanstalkGenerator`  |
| `app-runner`        | `AppRunnerGenerator`         |
| `batch`             | `BatchGenerator`             |
| `ec2-image-builder` | `EC2ImageBuilderGenerator`   |
| `lightsail`         | `LightsailGenerator`         |
| `ecr`               | `ECRGenerator`               |

### Analytics Services

| ServiceType        | Generator Class            |
|--------------------|----------------------------|
| `athena`           | `AthenaGenerator`          |
| `cloudsearch`      | `CloudSearchGenerator`     |
| `emr`             | `EMRGenerator`             |
| `glue`            | `GlueGenerator`            |
| `kinesis`         | `KinesisGenerator`         |
| `kinesis-firehose` | `KinesisFirehoseGenerator` |
| `msk`             | `MSKGenerator`             |
| `opensearch`      | `OpenSearchGenerator`      |
| `redshift`        | `RedshiftGenerator`        |

### Business Applications

| ServiceType | Generator Class    |
|-------------|--------------------|
| `connect`   | `ConnectGenerator` |
| `ses`       | `SESGenerator`     |
| `pinpoint`  | `PinpointGenerator`|

### Database Services

| ServiceType    | Generator Class          |
|----------------|--------------------------|
| `aurora`       | `AuroraGenerator`        |
| `documentdb`   | `DocumentDBGenerator`    |
| `elasticache`  | `ElastiCacheGenerator`   |
| `neptune`      | `NeptuneGenerator`       |
| `rds`          | `RDSGenerator`           |
| `timestream`   | `TimestreamGenerator`    |

### Developer Tools

| ServiceType    | Generator Class          |
|----------------|--------------------------|
| `codebuild`    | `CodeBuildGenerator`     |
| `codecommit`   | `CodeCommitGenerator`    |
| `codedeploy`   | `CodeDeployGenerator`    |
| `codepipeline` | `CodePipelineGenerator`  |

### Other Services

| ServiceType  | Generator Class        |
|--------------|------------------------|
| `appstream`  | `AppStreamGenerator`   |
| `amplify`    | `AmplifyGenerator`     |
| `gamelift`   | `GameLiftGenerator`    |

## HCL Renderer (`app/generators/hcl_renderer.py`)

`HCLRenderer` is the low-level renderer shared by all generators. All output uses two-space indentation.

Methods:
- `render_resource(block_type, name, attrs)` — `resource "type" "name" { ... }`
- `render_variable(name, var_type, description, default=None)` — `variable "name" { ... }`
- `render_output(name, value, description)` — `output "name" { ... }`
- `render_module(name, source, variables)` — `module "name" { ... }`
- `render_provider(provider, region)` — `provider "aws" { ... }`

Value formatting rules:
- Strings starting with `var.`, `module.`, `aws_`, `local.`, `data.` are passed through unquoted (Terraform references)
- Booleans render as `true`/`false`
- Nested dicts render as nested blocks
- Lists of dicts render as repeated blocks (e.g., DynamoDB `attribute` blocks)

## Service Generators

### LambdaGenerator (`app/generators/lambda_generator.py`)

Generates files for `aws_lambda_function` resources.

- `generate_resource_tf()` — `lambda.tf` with function_name, role, handler, runtime, optional memory_size/timeout/description/architectures/ephemeral_storage/environment_variables/layers/tags
- `generate_variables_tf()` — variables for all configured fields with defaults
- `generate_outputs_tf()` — outputs for function_arn and function_name
- `generate_iam_tf()` — `iam.tf` with `aws_iam_role` (Lambda assume-role policy) and `aws_iam_role_policy` referencing `iam-policies/{name}-policy.json` via `file()`

### S3Generator (`app/generators/s3_generator.py`)

Generates files for `aws_s3_bucket` resources.

- `generate_resource_tf()` — `s3.tf` with bucket name + `aws_s3_bucket_versioning` resource
- `generate_variables_tf()` — variables for bucket_name and versioning_enabled (default `"Enabled"`)
- `generate_outputs_tf()` — outputs for bucket_arn and bucket_name

### DynamoDBGenerator (`app/generators/dynamodb_generator.py`)

Generates files for `aws_dynamodb_table` resources.

- `generate_resource_tf()` — `dynamodb.tf` with table_name, billing_mode, hash_key, attribute blocks; optional range_key
- `generate_variables_tf()` — variables for table_name, billing_mode (default `PAY_PER_REQUEST`), hash_key, optional range_key
- `generate_outputs_tf()` — outputs for table_arn and table_name

### APIGatewayGenerator (`app/generators/api_gateway_generator.py`)

Generates files for `aws_apigatewayv2_api` resources. Supports enhanced configuration including routes, stages, authorizers, custom domains, VPC links, and throttling.

- `generate_resource_tf()` — `api-gateway.tf` with api_name, protocol_type, optional CORS, routes, stages, authorizers
- `generate_variables_tf()` — variables for api_name and protocol_type (default `HTTP`)
- `generate_outputs_tf()` — outputs for api_id and api_endpoint

### CloudWatchGenerator (`app/generators/cloudwatch_generator.py`)

Generates files for `aws_cloudwatch_log_group` resources.

- `generate_resource_tf()` — `cloudwatch.tf` with log_group_name, optional retention_in_days, kms_key_id, log_group_class
- `generate_variables_tf()` — variable for log_group_name, optional retention_in_days with default
- `generate_outputs_tf()` — output for log_group_arn

### IAMGenerator (`app/generators/iam_generator.py`)

Generates files for standalone IAM role and policy resources.

- `generate_resource_tf()` — `iam.tf` with `aws_iam_role` and `aws_iam_role_policy`
- `generate_variables_tf()` — variables for role_name, assume_role_policy, policy_name, policy_document
- `generate_outputs_tf()` — outputs for role_arn and role_name

### SNSGenerator (`app/generators/sns_generator.py`)

Generates files for `aws_sns_topic` resources.

- `generate_resource_tf()` — `sns.tf` with topic name, optional display_name, fifo_topic, content_based_deduplication, kms_master_key_id
- `generate_variables_tf()` — variables for topic configuration
- `generate_outputs_tf()` — outputs for topic_arn

### SQSGenerator (`app/generators/sqs_generator.py`)

Generates files for `aws_sqs_queue` resources.

- `generate_resource_tf()` — `sqs.tf` with queue name, optional visibility_timeout, message_retention, fifo_queue, delay_seconds, max_message_size
- `generate_variables_tf()` — variables for queue configuration
- `generate_outputs_tf()` — outputs for queue_arn and queue_url

## IAM Policy Generator (`app/generators/iam_policy_generator.py`)

`IAMPolicyGenerator` produces standalone JSON IAM policy documents (not HCL).

- `generate_policy_document(instance)` — consolidates base CloudWatch Logs permissions with all connection-derived IAM statements into a single JSON policy
- `generate_base_execution_policy(function_name)` — produces a minimal policy with only CloudWatch Logs permissions

Every Lambda instance gets a `{name}-policy.json` file in the `iam-policies/` directory.

## TfvarsGenerator (`app/generators/tfvars_generator.py`)

Generates `terraform.tfvars` and corresponding `variables.tf` blocks from resource `terraform_variables`.

- `generate_tfvars(instances, prefix=True)` — produces `terraform.tfvars` content with properly typed values (strings quoted, numbers/bools unquoted). When `prefix=True`, variable names are prefixed with the instance name to avoid collisions.
- `generate_variables_tf(instances, prefix=True)` — produces matching `variable` blocks with types and descriptions sourced from `VARIABLE_SCHEMAS`.

## GlobalConfigGenerator (`app/generators/global_config_generator.py`)

Generates project-level Terraform configuration files from `GlobalTerraformConfigIR`.

- `generate_backend_tf(config)` — `terraform { backend "..." { ... } }` block
- `generate_provider_tf(config)` — `provider "aws" { region, optional profile }` block
- `generate_versions_tf(config)` — `terraform { required_version, required_providers { aws { source, version } } }` block

## Variable Schemas (`app/generators/variable_schemas.py`)

`VARIABLE_SCHEMAS` is a `dict[ServiceType, list[VariableSchemaEntry]]` defining which Terraform variables each service type exposes. Used by `TfvarsGenerator` to produce correctly typed variable blocks, by `SchemaConfigForm` on the frontend to render dynamic config forms, and by the `/api/variable-schemas` endpoint.

### Schema Model Classes

| Class                  | Purpose                                                                 |
|------------------------|-------------------------------------------------------------------------|
| `VariableSchemaEntry`  | Schema for a single variable: `name`, `type`, `description`, `default`, `group`, `options`, `validation`, `visible_when` |
| `ValidationRule`       | Constraints: `min`, `max`, `pattern`, `pattern_description`, `allowed_values` |
| `OptionEntry`          | Predefined selectable option: `value`, `label`, `group`                 |
| `VisibleWhen`          | Conditional visibility: show variable only when `field` equals `equals` |

### Variables Per Service (Core)

| Service      | Count | Key Variables                                                          |
|--------------|-------|------------------------------------------------------------------------|
| Lambda       | 13    | function_name, handler, runtime, description, memory_size (128), timeout (3), ephemeral_storage_size (512), reserved_concurrent_executions, architectures, publish, layers, environment_variables, tags |
| S3           | 6     | bucket_name, versioning, force_destroy, object_lock_enabled, acceleration_status, tags |
| DynamoDB     | 12    | table_name, billing_mode, table_class, hash_key, hash_key_type, range_key, range_key_type, read_capacity, write_capacity, tags, point_in_time_recovery_enabled, deletion_protection_enabled |
| API Gateway  | 7     | api_name, protocol_type, description, cors_configuration, disable_execute_api_endpoint, route_selection_expression, tags |
| CloudWatch   | 5     | log_group_name, retention_in_days (30), kms_key_id, log_group_class, tags |

## Schema Validator (`app/generators/schema_validator.py`)

`validate_config_against_schema()` validates a `ResourceConfig` against the `VARIABLE_SCHEMAS` for a given service type. Called by both `/generate/json` and `/generate/zip` endpoints before IR building.

- Iterates each `VariableSchemaEntry` for the service type
- Evaluates `visible_when` conditions — skips validation for hidden fields
- Checks `ValidationRule` constraints: `min`/`max` bounds, `allowed_values`, `pattern` regex
- Raises `HTTPException(422)` on the first constraint violation
