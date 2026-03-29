# Backend API

The FastAPI application entry point, routers, middleware, and endpoint reference.

## Application Entry Point (`app/main.py`)

The FastAPI app is created in `app/main.py` with the title "Terraform IaC Generator". On startup it:

1. Adds CORS middleware (origin from `CORS_ORIGIN` env var, default `http://localhost:3000`)
2. Creates the persistence repository via `get_repository()`
3. Wraps the app with `SessionMiddleware` for anonymous cookie-based sessions
4. Registers the diagram CRUD router at `/api/diagrams`
5. Defines the Terraform generation endpoints inline

Service instances (`IRBuilder`, `CodeGenerator`, `OutputSerializer`) are created at module level and reused across requests.

## Middleware (`app/middleware/session_middleware.py`)

`SessionMiddleware` extends Starlette's `BaseHTTPMiddleware`. On every request it:

- Reads the `session_id` cookie
- If present and valid, touches the session (updates `last_active`) and sets `request.state.session_id`
- If missing or invalid, creates a new session via `SessionManager.create_session()` and sets a `session_id` cookie with `httponly=True`, `samesite=lax`, `max_age=2592000` (30 days)

## Routers

### Diagram CRUD (`app/routers/diagrams.py`)

Mounted at `/api/diagrams`. Uses a module-level `AbstractRepository` reference set during startup via `set_repository()`. All endpoints read `request.state.session_id` for session scoping.

## API Endpoints

### Diagram CRUD

| Method   | Path                    | Description                                      | Request Body         | Response                          |
|----------|-------------------------|--------------------------------------------------|----------------------|-----------------------------------|
| `POST`   | `/api/diagrams`         | Create a new diagram for the current session      | `DiagramStateInput`  | `{"id": "<uuid>"}`               |
| `GET`    | `/api/diagrams`         | List diagram summaries for the current session    | —                    | `DiagramSummary[]`                |
| `GET`    | `/api/diagrams/{id}`    | Load full diagram state (ownership-checked)       | —                    | `dict` (diagram_state)            |
| `PUT`    | `/api/diagrams/{id}`    | Update an existing diagram (ownership-checked)    | `DiagramStateInput`  | `{"id": "<uuid>"}`               |
| `DELETE` | `/api/diagrams/{id}`    | Delete a diagram (ownership-checked)              | —                    | `204 No Content`                  |

Ownership checks: `GET /{id}`, `PUT /{id}`, and `DELETE /{id}` compare `record.session_id` against the caller's session. Mismatches return `403 Forbidden`. Missing diagrams return `404`.

### Terraform Generation

| Method | Path             | Description                                        | Request Body               | Response                     |
|--------|------------------|----------------------------------------------------|----------------------------|------------------------------|
| `POST` | `/generate/json` | Generate Terraform files, return as JSON + summary | `ArchitectureDescription`  | `{"summary": ..., "files": ...}` |
| `POST` | `/generate/zip`  | Generate Terraform files, return as ZIP download   | `ArchitectureDescription`  | `application/zip` binary     |

Both endpoints run the same pipeline: validate each resource's config against `VARIABLE_SCHEMAS` via `validate_config_against_schema()`, then `IRBuilder.build()` → `CodeGenerator.generate()` → serialize. The `/generate/zip` endpoint sets `Content-Disposition` with the project name. Errors return `500` with a descriptive message; Pydantic validation failures return `422`; schema validation failures (out-of-range values, disallowed options) also return `422`.

### Variable Schemas

| Method | Path                      | Description                                      | Request Body | Response                          |
|--------|---------------------------|--------------------------------------------------|--------------|-----------------------------------|
| `GET`  | `/api/variable-schemas`   | Return all variable schemas keyed by service type | —            | `dict[str, list[dict]]`           |

Returns the full `VARIABLE_SCHEMAS` dictionary serialized as JSON. Each key is a service type value (e.g., `"lambda"`, `"s3"`), and each value is a list of schema entry objects with `name`, `type`, `description`, `default`, `group`, `options`, `validation`, and `visible_when` fields. Used by the frontend to drive the schema-based config form.

### Request Body: `ArchitectureDescription`

```json
{
  "project_name": "my-project",
  "environments": [{"name": "dev", "variables": {"region": "us-east-1"}}],
  "resources": [
    {
      "name": "my-func",
      "service_type": "lambda",
      "config": {"handler": "index.handler", "runtime": "python3.12"},
      "terraform_variables": {"function_name": "my-func", "memory_size": 256}
    }
  ],
  "connections": [
    {"source": "my-func", "target": "my-table", "connection_type": "reads_from"}
  ],
  "global_terraform_config": {
    "backend_type": "s3",
    "backend_config": {"bucket": "my-tf-state"},
    "provider_region": "us-east-1"
  }
}
```

### Response: `/generate/json`

```json
{
  "summary": {
    "project_name": "my-project",
    "environment_count": 1,
    "module_count": 1,
    "resource_instance_count": 1,
    "iam_policy_count": 1
  },
  "files": {
    "my-project/environments/dev/main.tf": "...",
    "my-project/modules/lambda/my-func/lambda.tf": "..."
  }
}
```

### Request Body: `DiagramStateInput`

```json
{
  "version": 3,
  "projectName": "my-project",
  "environments": [{"name": "dev", "variables": {}}],
  "elements": [{"id": "...", "type": "lambda", "x": 100, "y": 200, "name": "my-func"}],
  "connectors": [{"id": "...", "sourceId": "...", "targetId": "...", "type": "triggers"}],
  "viewport": {"x": 0, "y": 0, "zoom": 1.0},
  "globalTerraformConfig": {
    "backend_type": "local",
    "provider_region": "us-east-1"
  }
}
```
