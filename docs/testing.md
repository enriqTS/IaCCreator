# Testing

Test suites for both the Python backend (`tests/`) and the Next.js frontend (`frontend/__tests__/`).

## Backend Tests (`tests/`)

Run with: `pytest`

### Test Configuration

**`tests/conftest.py`** — shared fixtures and Hypothesis strategies:
- `resource_name_st` / `project_name_st` / `env_name_st` — regex-based name generators
- Per-service `ResourceConfig` strategies: `lambda_config_st`, `s3_config_st`, `dynamodb_config_st`, `api_gateway_config_st`, `cloudwatch_config_st`
- `resource_instance_strategy(service_type)` — generates valid `ResourceInstance` for a given type
- `architecture_description_strategy()` — generates full valid `ArchitectureDescription` with compatible connections
- `COMPATIBLE_CONNECTIONS` — set of valid `(source, target)` service type pairs

### Test Files

| File                            | Coverage                                                              |
|---------------------------------|-----------------------------------------------------------------------|
| `test_ir_builder.py`            | IR building: resource grouping, environment creation, connection validation, IAM derivation |
| `test_properties.py`            | Property-based tests (Hypothesis): round-trip IR building, HCL validity, file tree completeness |
| `test_unit.py`                  | Unit tests for individual generators, HCL renderer, output serializer |
| `test_validation.py`            | Input validation: missing fields, invalid service types, Pydantic 422 errors |
| `test_cors_and_wiring.py`       | CORS headers, middleware wiring, app startup                          |
| `test_diagram_router.py`        | Diagram CRUD router: create, list, get, update, delete, ownership checks |
| `test_diagram_crud.py`          | Property-based diagram CRUD: update-then-load roundtrip               |
| `test_persistence_roundtrip.py` | Property-based persistence: save/load roundtrip for TinyDB            |
| `test_session_manager.py`       | Session creation, resolution, touch                                   |
| `test_session_middleware.py`    | Middleware: cookie setting, session reuse, invalid cookie handling     |
| `test_session_isolation.py`     | Cross-session access returns 403                                      |
| `test_factory.py`               | Repository factory: env var switching, unknown backend error           |

## Frontend Tests (`frontend/__tests__/`)

Run with: `cd frontend && npx vitest run`

### Property-Based Tests (`frontend/__tests__/properties/`)

Uses fast-check for property-based testing (100+ iterations each).

| File                    | Properties Tested                                                    |
|-------------------------|----------------------------------------------------------------------|
| `viewport.test.ts`      | screenToCanvas/canvasToScreen roundtrip, zoom scale clamping, zoom cursor stability |
| `elements.test.ts`      | Element add/remove consistency, position updates, config merges      |
| `connectors.test.ts`    | Connector add/remove, orphan cleanup on element removal              |
| `state.test.ts`         | Undo/redo roundtrips, history stack limits                           |
| `serialization.test.ts` | Serialize/deserialize roundtrip preserves all state                  |

**`arbitraries.ts`** — shared fast-check arbitraries for generating random diagram elements, connectors, viewports, and configs.

### Unit Tests (`frontend/__tests__/unit/`)

| File                              | Coverage                                                    |
|-----------------------------------|-------------------------------------------------------------|
| `diagram-store.test.ts`           | Zustand store: element/connector CRUD, selection, viewport  |
| `diagram-store-persistence.test.ts` | Server persistence: save, load, list, delete              |
| `viewport.test.ts`                | Viewport utility functions                                  |
| `icon-registry.test.ts`           | AWS service icon lookup                                     |
| `storage.test.ts`                 | localStorage save/load/list/delete                          |
| `export.test.ts`                  | Terraform export: validation, API calls, error handling     |
| `config-forms.test.ts`            | Service config form rendering and updates                   |
| `tool-state.test.ts`              | Tool switching (pointer, connector, place-service)          |
| `hamburger-menu.test.tsx`         | Menu rendering and interactions                             |
| `dialogs.test.tsx`                | Dialog open/close, form submission                          |

### Other

| File                    | Coverage                          |
|-------------------------|-----------------------------------|
| `next-config.test.ts`   | Next.js config: API rewrites      |
