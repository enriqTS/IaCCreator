# Backend Models

Data models in `app/models/` define the Pydantic schemas for API input validation, internal representation (IR), and diagram state.

## Input Models (`app/models/input_models.py`)

These are the Pydantic schemas for incoming API requests (Terraform generation).

### `ServiceType` (Enum)

Supported AWS service types: `lambda`, `s3`, `api-gateway`, `dynamodb`, `iam`, `cloudwatch`.

### `ResourceConfig`

Service-specific configuration fields (all optional, used per service type):

| Field              | Type          | Used by      |
|--------------------|---------------|--------------|
| `handler`          | `str`         | Lambda       |
| `runtime`          | `str`         | Lambda       |
| `memory_size`      | `int`         | Lambda       |
| `timeout`          | `int`         | Lambda       |
| `is_layer`         | `bool`        | Lambda       |
| `versioning`       | `bool`        | S3           |
| `billing_mode`     | `str`         | DynamoDB     |
| `hash_key`         | `str`         | DynamoDB     |
| `hash_key_type`    | `str`         | DynamoDB     |
| `range_key`        | `str`         | DynamoDB     |
| `range_key_type`   | `str`         | DynamoDB     |
| `protocol_type`    | `str`         | API Gateway  |
| `retention_in_days`| `int`         | CloudWatch   |

### `ResourceInstance`

A named resource with `name`, `service_type`, and `config`. Includes a model validator that requires `hash_key` for DynamoDB resources.

### `Connection`

A connection between two resources: `source`, `target`, `connection_type` (e.g., `triggers`, `reads_from`, `writes_to`).

### `EnvironmentConfig`

An environment with `name` and `variables` (dict of string key-value pairs).

### `ArchitectureDescription`

Top-level input schema: `project_name`, `environments` (min 1), `resources` (min 1), `connections` (optional).

## IR Models (`app/models/ir_models.py`)

Internal representation models used between the IR builder and code generators.

### `FileTree`

Type alias: `dict[str, str]` — maps relative file paths to file contents.

### `IAMStatement`

A single IAM policy statement: `effect` (default `"Allow"`), `actions` (list of strings), `resources` (list of Terraform references).

### `ConnectionIR`

Normalized connection: `source_name`, `target_name`, `source_service`, `target_service`, `connection_type`.

### `ResourceInstanceIR`

Enriched resource instance: `name`, `service_type`, `config` (ResourceConfig), `iam_statements` (populated by IRBuilder from connections), `connections` (list of ConnectionIR).

### `ServiceModuleIR`

Groups all instances of a single service type: `service_type`, `instances`.

### `EnvironmentIR`

Environment with `name`, `variables`, and `module_refs` (list of ServiceType values this environment references).

### `ProjectIR`

Top-level IR: `project_name`, `environments`, `modules`, `connections`.

### `GeneratedFile`

A single generated file: `path` (relative), `content` (HCL or JSON string).

### `GenerationSummary`

Summary statistics: `project_name`, `environment_count`, `module_count`, `resource_instance_count`, `iam_policy_count`.

## Diagram Models (`app/models/diagram_models.py`)

Pydantic schemas for diagram state validation (save/load endpoints).

### `DiagramStateInput`

Top-level diagram state: `version` (int), `projectName`, `environments` (list of `EnvironmentConfigInput`), `elements` (list of `SerializedElementInput`), `connectors` (list of `SerializedConnectorInput`), `viewport` (`ViewportInput`).

### `SerializedElementInput`

Diagram element: `id`, `type`, `x`, `y`, `name`. Configured with `extra="allow"` for extensibility.

### `SerializedConnectorInput`

Diagram connector: `id`, `sourceId`, `targetId`, `type`. Configured with `extra="allow"`.

### `ViewportInput`

Viewport state: `x`, `y`, `zoom` (all floats).

### `EnvironmentConfigInput`

Environment: `name`, `variables` (dict, default empty).
