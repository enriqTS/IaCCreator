# Backend Generators

The `app/generators/` package contains HCL/Terraform code generators for each AWS service type, a shared HCL renderer, an IAM policy generator, and a registry that maps service types to generator instances.

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

`GENERATOR_REGISTRY` is a `dict[ServiceType, ServiceGenerator]` mapping each service type to a singleton generator instance:

| ServiceType    | Generator Class        |
|----------------|------------------------|
| `lambda`       | `LambdaGenerator`      |
| `s3`           | `S3Generator`          |
| `dynamodb`     | `DynamoDBGenerator`    |
| `api-gateway`  | `APIGatewayGenerator`  |
| `cloudwatch`   | `CloudWatchGenerator`  |
| `iam`          | `IAMGenerator`         |

Used by `FileTreeAssembler` to look up the correct generator when producing per-instance files.

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

- `generate_resource_tf()` — `lambda.tf` with function_name, role, handler, runtime, optional memory_size/timeout
- `generate_variables_tf()` — variables for function_name, handler, runtime, optional memory_size/timeout with defaults
- `generate_outputs_tf()` — outputs for function_arn and function_name
- `generate_iam_tf()` — `iam.tf` with `aws_iam_role` (Lambda assume-role policy) and `aws_iam_role_policy` referencing `iam-policies/{name}-policy.json` via `file()`

### S3Generator (`app/generators/s3_generator.py`)

Generates files for `aws_s3_bucket` resources.

- `generate_resource_tf()` — `s3.tf` with bucket name; if `versioning=true`, also generates `aws_s3_bucket_versioning`
- `generate_variables_tf()` — variable for bucket_name
- `generate_outputs_tf()` — outputs for bucket_arn and bucket_name

### DynamoDBGenerator (`app/generators/dynamodb_generator.py`)

Generates files for `aws_dynamodb_table` resources.

- `generate_resource_tf()` — `dynamodb.tf` with table_name, billing_mode, hash_key, attribute blocks; optional range_key
- `generate_variables_tf()` — variables for table_name, hash_key, optional range_key
- `generate_outputs_tf()` — outputs for table_arn and table_name

### APIGatewayGenerator (`app/generators/api_gateway_generator.py`)

Generates files for `aws_apigatewayv2_api` resources.

- `generate_resource_tf()` — `api-gateway.tf` with api_name and protocol_type (default `HTTP`)
- `generate_variables_tf()` — variable for api_name
- `generate_outputs_tf()` — outputs for api_id and api_endpoint

### CloudWatchGenerator (`app/generators/cloudwatch_generator.py`)

Generates files for `aws_cloudwatch_log_group` resources.

- `generate_resource_tf()` — `cloudwatch.tf` with log_group_name, optional retention_in_days
- `generate_variables_tf()` — variable for log_group_name, optional retention_in_days with default
- `generate_outputs_tf()` — output for log_group_arn

### IAMGenerator (`app/generators/iam_generator.py`)

Generates files for standalone IAM role and policy resources.

- `generate_resource_tf()` — `iam.tf` with `aws_iam_role` and `aws_iam_role_policy`
- `generate_variables_tf()` — variables for role_name, assume_role_policy, policy_name, policy_document
- `generate_outputs_tf()` — outputs for role_arn and role_name

## IAM Policy Generator (`app/generators/iam_policy_generator.py`)

`IAMPolicyGenerator` produces standalone JSON IAM policy documents (not HCL).

- `generate_policy_document(instance)` — consolidates base CloudWatch Logs permissions with all connection-derived IAM statements into a single JSON policy
- `generate_base_execution_policy(function_name)` — produces a minimal policy with only CloudWatch Logs permissions

Every Lambda instance gets a `{name}-policy.json` file in the `iam-policies/` directory.
