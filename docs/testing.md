# Testing

Test suites for both the Python backend (`tests/`) and the Next.js frontend (`frontend/__tests__/` and `frontend/src/utils/__tests__/`).

## Backend Tests (`tests/`)

Run with: `pytest -n auto` (parallelized via `pytest-xdist`; plain `pytest` also works but is slower)

Tests that need a `TestClient` against the real `app.main.app` (as opposed to a purpose-built minimal app) must isolate persistence with a `tmp_path`-backed repo — see the `client` fixtures in `test_cors_and_wiring.py`, `test_variable_schemas_endpoint.py`, and `test_properties.py`, and the note in `AGENTS.md`. Skipping this leaks writes into the real `data/db.json`, which gets corrupted under parallel test workers.

### Test Configuration

**`tests/conftest.py`** — shared fixtures and Hypothesis strategies:
- `resource_name_st` / `project_name_st` / `env_name_st` — regex-based name generators
- Per-service `ResourceConfig` strategies: `lambda_config_st`, `s3_config_st`, `dynamodb_config_st`, `api_gateway_config_st`, `cloudwatch_config_st`
- `resource_instance_strategy(service_type)` — generates valid `ResourceInstance` for a given type
- `any_resource_st` — generates a random resource across all six service types
- `connection_strategy(resources)` — generates valid connections between resources (only compatible pairs)
- `architecture_description_strategy()` — generates full valid `ArchitectureDescription` with unique names, unique environments, and compatible connections
- `COMPATIBLE_CONNECTIONS` — set of valid `(source, target)` service type pairs

### Test Files

| File                                              | Coverage                                                              |
|---------------------------------------------------|-----------------------------------------------------------------------|
| `test_ir_builder.py`                              | IR building: resource grouping, environment creation, connection validation, IAM derivation |
| `test_ir_builder_terraform_variables.py`          | Terraform variables propagation through IRBuilder, schema defaults, property tests |
| `test_properties.py`                              | Property-based tests (Hypothesis): round-trip IR building, HCL validity, file tree completeness |
| `test_unit.py`                                    | Unit tests for individual generators, HCL renderer, output serializer |
| `test_validation.py`                              | Input validation: missing fields, invalid service types, Pydantic 422 errors |
| `test_cors_and_wiring.py`                         | CORS headers, middleware wiring, app startup                          |
| `test_diagram_router.py`                          | Diagram CRUD router: create, list, get, update, delete, ownership checks |
| `test_diagram_crud.py`                            | Property-based diagram CRUD: update-then-load roundtrip               |
| `test_persistence_roundtrip.py`                   | Property-based persistence: save/load roundtrip for TinyDB            |
| `test_session_manager.py`                         | Session creation, resolution, touch                                   |
| `test_session_middleware.py`                       | Middleware: cookie setting, session reuse, invalid cookie handling     |
| `test_session_isolation.py`                       | Cross-session access returns 403                                      |
| `test_factory.py`                                 | Repository factory: env var switching, unknown backend error           |
| `test_global_config_generator.py`                 | GlobalConfigGenerator: backend.tf, provider.tf, versions.tf output    |
| `test_tfvars_generator.py`                        | TfvarsGenerator: string/number/bool formatting, prefix collision avoidance, variable block correspondence |
| `test_file_tree_assembler_terraform_variables.py` | Integration: file tree contains terraform.tfvars, backend.tf, provider.tf, versions.tf |
| `test_schema_content.py`                          | VARIABLE_SCHEMAS content: variable names per service, defaults, options, group assignments |
| `test_schema_serialization.py`                    | Property-based: VariableSchemaEntry serialization round-trip; all entries have non-empty groups |
| `test_schema_validator.py`                        | Property-based: backend rejects invalid values outside validation bounds; valid values pass |
| `test_variable_schemas_endpoint.py`               | GET /api/variable-schemas: returns 200, contains all service types, entries have required fields, options structure |

## Frontend Tests

### Property-Based Tests (`frontend/__tests__/properties/`)

Run with: `cd frontend && pnpm vitest run`

Uses fast-check for property-based testing (100+ iterations each).

| File                                          | Properties Tested                                                    |
|-----------------------------------------------|----------------------------------------------------------------------|
| `viewport.test.ts`                            | screenToCanvas/canvasToScreen roundtrip, zoom scale clamping, zoom cursor stability |
| `elements.test.ts`                            | Element add/remove consistency, position updates, config merges      |
| `connectors.test.ts`                          | Connector add/remove, orphan cleanup on element removal              |
| `state.test.ts`                               | Undo/redo roundtrips, history stack limits                           |
| `serialization.test.ts`                       | Serialize/deserialize roundtrip preserves all state                  |
| `canvas-objects-creation.test.ts`             | Canvas object creation for all object types                          |
| `canvas-objects-deletion.test.ts`             | Object deletion and cleanup                                          |
| `canvas-objects-deletion-selection.test.ts`   | Selection state after deletion                                       |
| `canvas-objects-cascade-delete.test.ts`       | Cascade deletion of anchored lines when parent object is removed     |
| `canvas-objects-selection.test.ts`            | Single and multi-selection behavior                                  |
| `canvas-objects-placement.test.ts`            | Object placement at correct positions                                |
| `canvas-objects-default-config.test.ts`       | Default visual configs applied on creation                           |
| `canvas-objects-min-dimensions.test.ts`       | Minimum dimension enforcement during resize                          |
| `canvas-objects-visual-config.test.ts`        | Visual config updates                                                |
| `canvas-objects-serialization.test.ts`        | Canvas object serialize/deserialize roundtrip                        |
| `canvas-objects-tabs.test.ts`                 | Correct tabs shown per object type                                   |
| `bottom-panel-*.test.ts` (10 files)           | Bottom panel: expand/collapse, height clamping, drag direction, layout mode, tab display, multi-selection |

**`arbitraries.ts`** — shared fast-check arbitraries for generating random diagram elements, connectors, viewports, canvas objects, and configs.

#### Subdirectory Tests

| Directory                                     | Coverage                                                    |
|-----------------------------------------------|-------------------------------------------------------------|
| `properties/architecture-search-panel/`       | Search: abbreviation expansion, case-insensitive/substring search, category ordering, click tool activation, recently-used capacity/ordering/persistence, text fallback (9 tests) |
| `properties/canvas-context-menu/`             | Context menu: copy/paste round-trip, delete, duplicate, fit-to-screen, group/ungroup, lock/unlock, rename, right-click selection, select-all, z-order operations (18 tests) |
| `properties/canvas-objects-editor/`           | Canvas editor: anchor detach/follow, empty text removal, icon scaling, label visibility, object creation type, picker search, ray-rect intersection, serialization round-trip, shape path validity, snap threshold, UML data persistence, v2→v3 migration (13 tests) |
| `properties/enhanced-variable-configuration/` | Schema config form rendering, visible_when conditional logic (2 tests) |
| `properties/fixed-connection-routing/`        | Connection routing: anchor stability, diagonal no-waypoints, drop threshold, facing anchors, global routing mode isolation, nearest anchor selection, orthogonal segments, perpendicular exit offset (8 tests) |
| `properties/sidebar-config-panel/`            | Sidebar panel: hamburger opposite side, layout prefs persistence, arch block tabs, deselection collapse, drag collapse, layout mode, multi-selection count, non-block tabs, selection expand, toggle collapse, width clamping/persistence (12 tests) |

### Additional Property Tests (`frontend/__tests__/property/`)

| File                                          | Properties Tested                                           |
|-----------------------------------------------|-------------------------------------------------------------|
| `drag-sizing-dimensions.property.test.ts`     | Drag sizing respects minimum dimensions                     |
| `group-membership.property.test.ts`           | Group membership consistency                                |
| `hollow-click-through.property.test.ts`       | Click-through on hollow (unfilled) geometric shapes         |
| `marquee-selection.property.test.ts`          | Marquee selection captures correct objects                  |
| `selection-set-correctness.property.test.ts`  | Selection set invariants                                    |
| `serialization-roundtrip.property.test.ts`    | Full serialization roundtrip with canvas objects            |
| `undo-redo-canvas.property.test.ts`           | Undo/redo for canvas object operations                      |
| `undo-redo-preservation.property.test.ts`     | Undo/redo preserves all state correctly                     |
| `viewport-transform.property.test.ts`         | Viewport transform properties                               |
| `z-order-uniqueness.property.test.ts`         | Z-order values remain unique across objects                 |

### Unit Tests (`frontend/__tests__/unit/`)

| File                                          | Coverage                                                    |
|-----------------------------------------------|-------------------------------------------------------------|
| `diagram-store.test.ts`                       | Zustand store: element/connector CRUD, selection, viewport  |
| `diagram-store-canvas-actions.test.ts`        | Canvas object actions: add, update, remove, select          |
| `diagram-store-persistence.test.ts`           | Server persistence: save, load, list, delete                |
| `diagram-types.test.ts`                       | Type guards and utility functions for diagram types         |
| `viewport.test.ts`                            | Viewport utility functions                                  |
| `icon-registry.test.ts`                       | AWS service icon lookup                                     |
| `storage.test.ts`                             | localStorage save/load/list/delete                          |
| `export.test.ts`                              | Terraform export: validation, API calls, error handling     |
| `config-forms.test.ts`                        | Service config form rendering and updates                   |
| `tool-state.test.ts`                          | Tool switching (pointer, connector, place-service)          |
| `hamburger-menu.test.tsx`                     | Menu rendering and interactions                             |
| `dialogs.test.tsx`                            | Dialog open/close, form submission                          |
| `bottom-panel.test.tsx`                       | Bottom panel rendering and interactions                     |
| `bottom-panel-grouping.test.tsx`              | Grouping/ungrouping from bottom panel                       |
| `architecture-block-component.test.tsx`       | Architecture block rendering                                |
| `block-visual-config.test.tsx`                | Block visual config panel                                   |
| `delete-object.test.tsx`                      | Object deletion interactions                                |
| `drag-sizing-overlay.test.tsx`                | Drag sizing overlay behavior                                |
| `element-layer.test.tsx`                      | Element layer rendering and interactions                    |
| `placement-preview.test.tsx`                  | Placement preview ghost rendering                           |
| `global-terraform-config-panel.test.tsx`      | Global Terraform config panel                               |
| `terraform-variables-store.test.ts`           | Terraform variable store operations                         |
| `variables-panel.test.tsx`                    | Variables panel rendering                                   |
| `visual-tab.test.tsx`                         | Visual tab dispatching                                      |
| `z-order-controls.test.tsx`                   | Z-order control buttons                                     |
| `z-order-store.test.ts`                       | Z-order store operations                                    |
| `object-picker-menu.test.tsx`                 | Object picker menu rendering and search                     |
| `recently-used-store.test.ts`                 | Recently used store: add, deduplicate, capacity cap         |
| `routing.test.ts`                             | Orthogonal connection routing waypoint computation           |
| `schema-store.test.ts`                        | Schema store: fetch, cache, fallback to bundled schemas     |
| `fixed-connection-routing.test.ts`            | Fixed connection routing unit tests                         |

### API Client Tests (`frontend/src/utils/__tests__/`)

| File                    | Coverage                                                              |
|-------------------------|-----------------------------------------------------------------------|
| `api-client.test.ts`   | Property-based: structured errors for non-2xx, network errors, credentials inclusion; unit: exports, base URL config |

### Other

| File                    | Coverage                          |
|-------------------------|-----------------------------------|
| `next-config.test.ts`   | Next.js config: API rewrites      |
