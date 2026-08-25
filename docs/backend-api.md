# Backend API

The FastAPI application in `app/main.py` converts an architecture description into Terraform and persists anonymous-session diagrams.

## Application setup

The app configures CORS from `CORS_ORIGIN` (default `http://localhost:3000`), creates a repository through `get_repository()`, and adds `SessionMiddleware`. The middleware creates or resumes the 30-day `session_id` cookie and exposes it as `request.state.session_id`.

`app/routers/diagrams.py` is mounted at `/api/diagrams`. Its repository is a FastAPI dependency (`get_repo`), so tests can override it through `app.dependency_overrides`.

## Endpoints

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/generate/json` | `ArchitectureDescription` | `GenerationResponse` |
| POST | `/generate/zip` | `ArchitectureDescription` | ZIP download |
| POST | `/api/import/openapi` | `OpenApiImportRequest` | `OpenApiImportResponse` |
| GET | `/api/naming-rules` | — | `NamingRulesResponse` |
| GET | `/api/variable-schemas` | — | `VariableSchemasResponse` |
| GET | `/api/connection-schemas` | — | `ConnectionSchemasResponse` |
| GET | `/api/editor-bootstrap` | — | `EditorBootstrapResponse` |
| POST | `/api/resources/initialize` | `ResourceInitializationRequest` | `ResourceInitializationResponse` |
| POST | `/api/connections/preview` | `ArchitectureDescription` | `ConnectionPreviewResponse` |
| POST | `/api/diagrams/architecture` | `DiagramStateInput` | `ArchitectureDescription` |
| POST | `/api/diagrams/generate/json` | `DiagramStateInput` | `GenerationResponse` |
| POST | `/api/diagrams/generate/zip` | `DiagramStateInput` | ZIP download |
| POST | `/api/diagrams/connections/preview` | `DiagramStateInput` | `ConnectionPreviewResponse` |
| POST | `/api/diagrams/connections/apply` | `ApplyConnectionOperationRequest` | `DiagramStateInput` |
| POST | `/api/diagrams` | `DiagramStateInput` | diagram ID |
| GET | `/api/diagrams` | — | session-scoped diagram summaries |
| GET | `/api/diagrams/{diagram_id}` | — | saved diagram state |
| PUT | `/api/diagrams/{diagram_id}` | `DiagramStateInput` | diagram ID |
| DELETE | `/api/diagrams/{diagram_id}` | — | `204 No Content` |

Generation validates each typed service config, builds a `ProjectIR`, generates its file tree, and serializes it. Domain and validation errors become client responses; unexpected generation failures become `500` responses.

`/api/connections/preview` builds the same IR and returns each connection's generated resources, IAM grants, and warnings. The editor uses this rather than inferring Terraform behavior.

`/api/variable-schemas` introspects the typed per-service configuration models and their `TerraformField` metadata. `/api/connection-schemas` exposes the connection registry's labels, defaults, and editable fields. `/api/naming-rules` exposes the backend rule applied to Terraform resource names.

## Architecture payload

`ArchitectureDescription` contains a project name, at least one environment and resource, optional connections, and global Terraform configuration. Resources may carry a stable `id`; connections may carry `source_id` and `target_id`, allowing the backend to resolve endpoints after a rename. Names remain in the payload for generated Terraform labels and backward compatibility.

```json
{
  "project_name": "my-project",
  "environments": [{"name": "dev", "variables": {"region": "us-east-1"}}],
  "resources": [{
    "id": "resource-1",
    "name": "my-function",
    "service_type": "lambda",
    "config": {"handler": "index.handler", "runtime": "python3.12"}
  }],
  "connections": [],
  "global_terraform_config": {"provider_region": "us-east-1"}
}
```

Diagram CRUD is session scoped. Writes normalize and validate state before persistence, and reads return the canonical current version. Reading, updating, or deleting a diagram owned by another session returns `403`; a missing diagram returns `404`.

The editor bootstrap describes backend support and domain defaults. Resource initialization derives unique names, typed config defaults, and Terraform variable defaults. Diagram-based generation and preview convert canonical canvas state on the backend; the direct `/generate/*` endpoints remain available for API consumers.

Linked connection entry creation, editing, and removal use `/api/diagrams/connections/apply`. The backend resolves the connection registry metadata, materializes templates and target bindings, and returns canonical diagram state; the frontend only submits user intent.
