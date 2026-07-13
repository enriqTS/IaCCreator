# Backend Services

The service layer in `app/services/` contains the business logic for IR construction, Terraform code generation, connection processing, file tree assembly, output serialization, and session management.

## IRBuilder (`app/services/ir_builder.py`)

Transforms a validated `ArchitectureDescription` into a `ProjectIR`.

- `build(input: ArchitectureDescription) -> ProjectIR`
  1. Validates all connections reference existing resources and compatible service pairs
  2. Groups resources by `ServiceType` into `ServiceModuleIR` instances
  3. Derives IAM statements from connections (e.g., Lambda → DynamoDB adds DynamoDB read/write actions)
  4. Builds `EnvironmentIR` entries with `module_refs` pointing to all used service types
  5. Propagates `terraform_variables` from each `ResourceInstance` to `ResourceInstanceIR`
  6. Builds `GlobalTerraformConfigIR` from the input's `global_terraform_config`
  7. Returns the complete `ProjectIR`

Compatible connection pairs (defined in `COMPATIBLE_CONNECTIONS`):
- API Gateway → Lambda
- Lambda → DynamoDB
- Lambda → S3
- Lambda → CloudWatch
- Lambda → SNS
- Lambda → SQS
- SQS → Lambda
- SNS → SQS
- SNS → Lambda

Invalid connections (unknown resources, incompatible pairs) raise `HTTPException(422)`.

IAM action mappings per target service (defined in `IAM_ACTIONS`):
- DynamoDB: GetItem, PutItem, Query, Scan, UpdateItem, DeleteItem
- S3: GetObject, PutObject, DeleteObject, ListBucket
- CloudWatch: CreateLogGroup, CreateLogStream, PutLogEvents
- SNS: Publish
- SQS: SendMessage

## CodeGenerator (`app/services/code_generator.py`)

Top-level orchestrator that produces a `FileTree` from a `ProjectIR`.

- `generate(project: ProjectIR) -> FileTree`
  1. Runs `ConnectionProcessor.process_all()` to produce integration files and enrich IAM statements
  2. Runs `FileTreeAssembler.assemble()` with the enriched IR and extra files

## ConnectionProcessor (`app/services/connection_processor.py`)

A thin facade (~30 lines) that iterates project connections and dispatches each one to the appropriate handler via the connection handler registry. It does not contain any connection-specific logic itself.

- `process_all(project: ProjectIR) -> list[GeneratedFile]` — iterates all connections, looks up the handler in `CONNECTION_HANDLER_REGISTRY`, and delegates. Logs a warning and skips if no handler is registered for a given connection type pair.

## Connection Handlers Package (`app/services/connection_handlers/`)

All connection-specific logic lives in dedicated handler classes under this package. The architecture follows the same Protocol + registry pattern used by `app/generators/`.

### Package Structure

```
app/services/connection_handlers/
├── __init__.py              # Exports ConnectionHandler, BaseConnectionHandler
├── base.py                  # ConnectionHandler Protocol + BaseConnectionHandler
├── registry.py              # CONNECTION_HANDLER_REGISTRY dict
├── apigw_lambda.py          # ApiGatewayLambdaHandler
├── lambda_dynamodb.py       # LambdaDynamoDBHandler
├── lambda_s3.py             # LambdaS3Handler
├── lambda_cloudwatch.py     # LambdaCloudWatchHandler
├── lambda_sns.py            # LambdaSNSHandler
├── lambda_sqs.py            # LambdaSQSHandler
├── sqs_lambda.py            # SQSLambdaHandler
├── sns_sqs.py               # SNSSQSHandler
└── sns_lambda.py            # SNSLambdaHandler
```

### Handler Interface (`base.py`)

`ConnectionHandler` is a `typing.Protocol` defining the single method every handler must implement:

```python
class ConnectionHandler(Protocol):
    def handle(self, connection: ConnectionIR, project: ProjectIR) -> list[GeneratedFile]: ...
```

`BaseConnectionHandler` is a concrete base class that provides shared utilities:

- `self._renderer` — an `HCLRenderer` instance for generating Terraform HCL
- `_attach_iam_statement(lambda_name, statement, project)` — finds the Lambda `ResourceInstanceIR` and appends an IAM statement
- `_find_instance(name, project)` — looks up a resource instance by name across all project modules

Concrete handlers inherit from `BaseConnectionHandler` (which structurally satisfies the `ConnectionHandler` protocol).

### Registry (`registry.py`)

`CONNECTION_HANDLER_REGISTRY` is a module-level dict mapping `(ServiceType, ServiceType)` tuples to handler instances:

| Source → Target          | Handler Class               | Action                                                                 |
|--------------------------|-----------------------------|------------------------------------------------------------------------|
| API Gateway → Lambda     | `ApiGatewayLambdaHandler`   | Generates integration, route(s), and permission HCL. Supports multi-route via `routes` array in `connection_config`, `integration_type`, `payload_format_version`, `vpc_link_name`, `connection_role` |
| Lambda → DynamoDB        | `LambdaDynamoDBHandler`     | Attaches DynamoDB IAM statements based on `access_pattern` (no files)  |
| Lambda → S3              | `LambdaS3Handler`           | Attaches S3 access IAM statements based on `access_pattern` (no files) |
| Lambda → CloudWatch      | `LambdaCloudWatchHandler`   | Generates `aws_cloudwatch_log_group` HCL + attaches CloudWatch IAM     |
| Lambda → SNS             | `LambdaSNSHandler`          | Attaches `sns:Publish` IAM statement (no files)                        |
| Lambda → SQS             | `LambdaSQSHandler`          | Attaches `sqs:SendMessage` IAM statement (no files)                    |
| SQS → Lambda             | `SQSLambdaHandler`          | Generates event source mapping + Lambda permission HCL. Attaches SQS read IAM. Supports `batch_size` and `maximum_batching_window_in_seconds` |
| SNS → SQS                | `SNSSQSHandler`             | Generates SNS topic subscription + SQS queue policy HCL               |
| SNS → Lambda             | `SNSLambdaHandler`          | Generates SNS topic subscription + Lambda permission HCL              |

IAM statements are mutated in-place on `ResourceInstanceIR.iam_statements`.

### How to Add a New Connection Handler

1. **Create handler file** — `app/services/connection_handlers/{source}_{target}.py`
2. **Create handler class** — inherit from `BaseConnectionHandler`:
   ```python
   from app.services.connection_handlers.base import BaseConnectionHandler
   from app.models.ir_models import ConnectionIR, GeneratedFile, ProjectIR

   class SourceTargetHandler(BaseConnectionHandler):
       def handle(self, connection: ConnectionIR, project: ProjectIR) -> list[GeneratedFile]:
           # Generate HCL files and/or attach IAM statements
           ...
           return [...]
   ```
3. **Implement `handle`** — use `self._renderer` to generate HCL, `self._attach_iam_statement()` for IAM mutations, and return any `GeneratedFile` objects produced.
4. **Register in `registry.py`** — add the `(ServiceType.SOURCE, ServiceType.TARGET)` tuple mapped to a handler instance:
   ```python
   from app.services.connection_handlers.source_target import SourceTargetHandler

   CONNECTION_HANDLER_REGISTRY: dict[...] = {
       ...
       (ServiceType.SOURCE, ServiceType.TARGET): SourceTargetHandler(),
   }
   ```

That's it — `ConnectionProcessor` picks up new handlers automatically via the registry.

## FileTreeAssembler (`app/services/file_tree_assembler.py`)

Walks the `ProjectIR` and collects all generated content into a `FileTree` (dict of path → content).

- `assemble(project, extra_files) -> FileTree`
  1. Environment files: `main.tf` (provider + module blocks), `variables.tf`, `outputs.tf`, `terraform.tfvars`, `backend.tf`, `provider.tf`, `versions.tf`
  2. Service module files: module-level `main.tf`/`variables.tf`/`outputs.tf` + per-instance subfolders
  3. Per-instance files: `{service}.tf`, `variables.tf`, `outputs.tf` (Lambda also gets `iam.tf`)
  4. IAM policy JSON files: `{name}-policy.json` in `iam-policies/` for every Lambda
  5. Merges `extra_files` from connection processing

Uses `GENERATOR_REGISTRY` to look up the correct generator for each service type. Uses `TfvarsGenerator` to produce `terraform.tfvars` and corresponding variable blocks from resource `terraform_variables`. Uses `GlobalConfigGenerator` to produce `backend.tf`, `provider.tf`, and `versions.tf` from `GlobalTerraformConfigIR`.

## OutputSerializer (`app/services/output_serializer.py`)

Converts a `FileTree` into downloadable formats.

- `to_zip(file_tree) -> bytes` — produces a ZIP archive (ZIP_DEFLATED) with sorted paths
- `to_json(file_tree, summary) -> dict` — returns `{"files": ..., "summary": ...}`

## SessionManager (`app/services/session_manager.py`)

Manages anonymous session lifecycle. Takes an `AbstractRepository` dependency.

- `create_session() -> str` — generates UUID v4, creates a `UserRecord`, returns the session ID
- `resolve_session(session_id) -> UserRecord | None` — looks up a session
- `touch_session(session_id)` — updates `last_active` timestamp

## Service Interaction Flow

```
ArchitectureDescription
        │
        ▼
    IRBuilder.build()
        │
        ▼
     ProjectIR
        │
        ▼
  CodeGenerator.generate()
        │
        ├── ConnectionProcessor.process_all()
        │       │
        │       ├── Integration HCL files (API GW integrations, routes,
        │       │     permissions, event source mappings, subscriptions, policies)
        │       └── IAM statement enrichment (mutates ProjectIR)
        │
        └── FileTreeAssembler.assemble()
                │
                ├── Environment files (main.tf, variables.tf, outputs.tf,
                │     terraform.tfvars, backend.tf, provider.tf, versions.tf)
                ├── Module files
                ├── Instance files (via GENERATOR_REGISTRY)
                ├── IAM policy JSON files
                └── Extra files from connections
                        │
                        ▼
                    FileTree
                        │
                        ▼
              OutputSerializer.to_zip() / .to_json()
```
