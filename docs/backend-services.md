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

Invalid connections (unknown resources, incompatible pairs) raise `HTTPException(422)`.

IAM action mappings per target service (defined in `IAM_ACTIONS`):
- DynamoDB: GetItem, PutItem, Query, Scan, UpdateItem, DeleteItem
- S3: GetObject, PutObject, DeleteObject, ListBucket
- CloudWatch: CreateLogGroup, CreateLogStream, PutLogEvents

## CodeGenerator (`app/services/code_generator.py`)

Top-level orchestrator that produces a `FileTree` from a `ProjectIR`.

- `generate(project: ProjectIR) -> FileTree`
  1. Runs `ConnectionProcessor.process_all()` to produce integration files and enrich IAM statements
  2. Runs `FileTreeAssembler.assemble()` with the enriched IR and extra files

## ConnectionProcessor (`app/services/connection_processor.py`)

Processes resource connections and generates integration HCL and IAM statements. Uses a dispatch table mapping `(source_service, target_service)` tuples to handler methods.

- `process_all(project: ProjectIR) -> list[GeneratedFile]` — iterates all connections
- `process(connection, project) -> list[GeneratedFile]` — dispatches to a handler based on service pair

Connection handlers:

| Source → Target          | Action                                                                 |
|--------------------------|------------------------------------------------------------------------|
| API Gateway → Lambda     | Generates `aws_apigatewayv2_integration` HCL file                     |
| Lambda → DynamoDB        | Attaches DynamoDB IAM statements to the Lambda instance (no files)     |
| Lambda → S3              | Attaches S3 IAM statements to the Lambda instance (no files)           |
| Lambda → CloudWatch      | Generates `aws_cloudwatch_log_group` HCL + attaches CloudWatch IAM    |

IAM statements are mutated in-place on `ResourceInstanceIR.iam_statements`.

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
        │       ├── Integration HCL files (API GW integrations, log groups)
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
