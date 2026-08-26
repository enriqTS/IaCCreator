# Backend Models

`app/models/` contains request models, typed service configuration, the generation IR, persistence models, and API response models.

## Input models

`app/models/input_models/` is a package, not a monolithic model file. `_general.py` defines cross-cutting models:

- `ServiceType` includes generated services and icon-only catalog services.
- `ResourceInstance` has optional stable `id`, `name`, `service_type`, a typed service config, and Terraform-variable overrides.
- `Connection` has source/target names plus optional `source_id`/`target_id`, `connection_type`, and `connection_config`.
- `EnvironmentConfig`, `GlobalTerraformConfig`, and `ArchitectureDescription` complete the generation request.

Every generated service has a dedicated config model, such as `lambda_config.py`, `eventbridge_config.py`, or the Bedrock-family models. `ResourceInstance` resolves a plain incoming config object to the registered typed model. `TerraformField` metadata on these models supplies the frontend schema and backend validation rules.

Resource names are validated for Terraform-safe syntax and uniqueness. Stable IDs let connection endpoint resolution survive a rename.

## Connection and response models

`app/models/connection_configs/` defines editable connection configuration and schema response models. The connection-handler registry is the source of truth for valid service pairs and connection types.

`connection_previews.py` models connection contributions and warnings returned by the preview endpoint. `response_models.py` contains typed generation, variable-schema, and naming-rule responses. OpenAPI import has dedicated request/response models under `app/services/openapi/models.py`.

## IR models

`app/models/ir_models.py` is the internal boundary between validation and generation.

- `ProjectIR` contains environments, service modules, normalized connections, and global configuration.
- `ResourceInstanceIR` retains typed config, Terraform variables, connections, and collected IAM statements.
- `ConnectionIR` preserves source/target names and stable IDs.
- `ConnectionContribution` carries `ModuleInput`, `ModuleOutput`, `ModuleResource`, and `IAMGrant` values from handlers to the assembler.
- `GenerationSummary` and `FileTree` represent generated output.

## Diagram and persistence models

`DiagramStateInput` validates persisted diagram requests. Diagram storage is versioned and upgraded through `services/diagram_migrations.py` when read. The current format is a discriminated canvas-object union covering architecture blocks, lines with anchors and waypoints, geometric/text/UML objects, typed visuals, connectors, groups, viewport, global configuration, and routing mode. Partial resource and connection configurations are shape-validated against their registered backend models while drafts may omit required generation fields. See `frontend/src/types/serialization.ts` for the client serialization contract.

Persistence records (`UserRecord`, `DiagramRecord`, and `DiagramSummary`) live in `app/persistence/models.py`.
