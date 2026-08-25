# Backend Services

The service layer turns validated requests into a Terraform file tree and owns connection, session, migration, and OpenAPI-import processing.

## Generation flow

```
ArchitectureDescription
  -> IRBuilder.build()
  -> CodeGenerator.generate()
  -> ConnectionProcessor.process_all()
  -> FileTreeAssembler.assemble()
  -> OutputSerializer
```

`IRBuilder` resolves typed resources, validates and normalizes connections, resolves stable endpoint IDs, groups instances by service, and produces `ProjectIR`. Valid connection kinds are derived from `CONNECTION_SPECS`, not a separate compatibility table.

`CodeGenerator` obtains one merged `ConnectionContribution` from `ConnectionProcessor` and passes it to `FileTreeAssembler`. `OutputSerializer` returns JSON or a ZIP; ZIP generation can strip the project prefix for downloads.

## Connections

`app/services/connection_handlers/registry.py` is the single source of truth. Each `ConnectionSpec` defines source and target service types, a connection type, label, default selection, config model, and handler. `resolve_spec()` supports exact matches, legacy API Gateway roles, and the default for an unambiguous pair.

Handlers return `ConnectionContribution`, not generated files alone. A contribution can add module inputs, outputs, module-owned HCL resources, and IAM grants. `ConnectionProcessor` merges all contributions, then attaches grants to the instance owning the execution role.

The current registry includes API Gateway route-handler and authorizer connections; Lambda, ECS, S3, DynamoDB, SNS, and SQS wiring; DynamoDB streams; and EventBridge targets. Handler implementations include parameterized IAM grants, API Gateway/Lambda, S3/Lambda notifications, DynamoDB/Lambda streams, EventBridge targets, SNS subscriptions, and SQS event sources.

`ConnectionPreviewer` invokes the same handler behavior to return generated resources, IAM grants, and handler-reported issues for the editor.

## File assembly

`FileTreeAssembler` writes environment Terraform and categorized, per-instance service modules. It adds connection resources only to the module that owns them and extends recipient module variable/output files for cross-module wiring. Execution roles and policy documents are generated for any service config that declares ownership, rather than being special-cased to Lambda.

## Other services

- `SessionManager` creates, resolves, and touches anonymous-session users through `AbstractRepository`.
- `diagram_migrations.py` upgrades persisted diagram state on read.
- `services/openapi/` parses an OpenAPI document and maps it to API Gateway configuration for `/api/import/openapi`.
