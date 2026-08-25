# Implementation Plan: Backend-Owned Editor Domain

## Goal

Make the frontend a canvas renderer and interaction client. Domain rules, defaults, naming, diagram normalization, persistence migration, and conversion from editor state to Terraform input must be owned by the backend and exposed through typed APIs.

Canvas-local behavior remains frontend-owned: geometry, hit-testing, routing, selection, undo/redo, drag previews, visual styling, and browser download behavior.

## Current gaps

The frontend currently duplicates or performs domain work in these locations:

| Concern | Current frontend location | Target owner |
|---|---|---|
| Diagram-to-generation conversion | `store/slices/serialization-slice.ts` | Backend |
| Default Terraform variables | `types/terraform-variables.ts` | Backend typed config models |
| Default resource names | `utils/name-utils.ts` | Backend |
| Export required-field validation | `utils/export.ts` | Backend |
| Primary save/load workflow | `app/page.tsx`, `utils/storage.ts` | Backend repository and migrations |
| Supported/placable service status | `data/object-catalog.ts`, icon registry | Backend service catalog |
| Connection-linked config materialization | connection field renderers | Backend command/normalization path |

## API design principles

1. Every endpoint has typed request and response models.
2. The frontend sends editor intent and diagram state; it does not reproduce backend rules.
3. The backend returns canonicalized state or structured field errors.
4. Existing generation endpoints remain backward compatible during migration, then converge on canonical diagram input.
5. Presentation-only data may stay local: icons, shape paths, shortcut labels, visual defaults, and geometry.

## Phase 1: Define canonical editor contracts

### 1.1 Create backend diagram-state models

Extend or replace `app/models/diagram_models.py` so it models the actual serialized frontend diagram format:

- canvas objects and their discriminated types;
- architecture-block config and Terraform variables;
- lines, anchors, and waypoints;
- connectors and connection configuration;
- viewport, groups, global Terraform config, and routing mode.

The request model must accept the state emitted by `serializeDiagramState()` without legacy `elements` requirements or incompatible viewport fields.

### 1.2 Centralize normalization

Create a backend diagram-normalization service that:

- migrates old diagram versions;
- fills backend-owned resource defaults;
- fills visual defaults only when the backend owns persisted normalization;
- validates service types, object types, connector references, and configuration shape;
- returns the current canonical diagram version.

Use it from diagram reads and writes. Remove duplicate migration/default logic where possible.

### 1.3 Add typed responses

Add response models for diagram CRUD, including create/update IDs, summaries, and full canonical diagram state. Do not leave router responses as anonymous dictionaries.

### Acceptance criteria

- A current frontend serialized diagram validates without compatibility shims in the frontend.
- Saving and then loading returns canonical current-version state.
- Invalid canvas references and invalid domain configuration produce structured `422` responses.
- OpenAPI describes all diagram payloads and responses.

## Phase 2: Backend-owned catalog, defaults, and names

### 2.1 Add editor bootstrap endpoint

Add `GET /api/editor-bootstrap` with a typed response containing:

- service catalog entries: service type, display name, category, generator/support status;
- variable schemas and connection schemas, or explicit versioned references to their existing endpoints;
- naming rule metadata;
- canonical global Terraform defaults;
- current diagram format version.

The frontend may merge catalog entries with its local icon registry by service type. It must not infer support status from icon data.

### 2.2 Add resource initialization endpoint

Add `POST /api/resources/initialize`. The request supplies the requested service type and the current resource names or canonical diagram context. The response supplies:

- a backend-derived unique default name;
- typed config defaults;
- Terraform-variable defaults;
- any backend-defined initial state needed by the editor.

Use a request/response rather than reproducing naming counters or schema fallbacks in the browser.

### 2.3 Remove frontend domain defaults

After the endpoint is integrated, remove frontend `getDefaultVariables()` as the authority and remove `generateDefaultName()` from normal block creation. Retain only visual object defaults needed for immediate canvas rendering.

### Acceptance criteria

- Placing a resource uses a backend-provided name and defaults.
- Changing a backend schema/default requires no frontend domain-code edit.
- A service can be shown with a local icon but is only placeable when the backend catalog says it is supported.

## Phase 3: Server-side architecture conversion and generation

### 3.1 Add diagram conversion service

Create a backend service that converts canonical diagram state to `ArchitectureDescription`. It owns:

- extraction of architecture blocks;
- resource IDs, names, typed configs, and Terraform variables;
- connector endpoint resolution and connection direction;
- default environment behavior;
- translation of global Terraform configuration.

This service is the only place that performs editor-format to generation-format transformation.

### 3.2 Add diagram-based endpoints

Add typed endpoints, for example:

| Endpoint | Request | Response |
|---|---|---|
| `POST /api/diagrams/architecture` | canonical diagram state | `ArchitectureDescription` |
| `POST /api/diagrams/generate/zip` | canonical diagram state | ZIP download |
| `POST /api/diagrams/generate/json` | canonical diagram state | `GenerationResponse` |
| `POST /api/diagrams/connections/preview` | canonical diagram state | `ConnectionPreviewResponse` |

They should normalize state, convert it, then call the existing generation/preview pipeline. Keep `/generate/*` temporarily for direct API consumers.

### 3.3 Replace frontend export conversion

Remove `serializeToArchitectureDescription()` from the frontend generation path. The frontend submits `serializeDiagramState()` to the diagram-based generation and preview endpoints.

Remove `ALWAYS_REQUIRED` and export-time domain validation from `utils/export.ts`. Display structured backend validation errors instead.

### Acceptance criteria

- The frontend no longer maps canvas objects/connectors to Terraform resources/connections.
- The same submitted diagram yields identical preview and generation behavior.
- Generation rejects invalid diagrams through backend errors, with errors displayable by object/field identity.

## Phase 4: Make server persistence primary

### 4.1 Route Save/Load through diagram APIs

Change the hamburger-menu Save/Load actions to use `persistence-slice.ts` and `/api/diagrams`. The server must normalize on write and migrate on read.

### 4.2 Demote local storage to drafts

Either remove `utils/storage.ts` or explicitly present it as offline draft export/import. It must not be the default saved-diagram workflow and must not become an alternate migration authority.

### Acceptance criteria

- Normal Save/Load survives reload and uses the anonymous-session repository.
- Loading an older saved server diagram returns canonical migrated state.
- Local drafts, if retained, are clearly offline-only and are normalized when sent to the backend.

## Phase 5: Move connection mutations behind backend normalization

The backend already supplies connection schemas and templates. Complete ownership by adding a typed operation for applying connection edits, or by making diagram normalization materialize/validate linked entries consistently.

The frontend should render generic fields and submit user-selected values. It may stage form values locally, but it must not be the authority for creating API Gateway route entries or applying connection template semantics.

### Acceptance criteria

- Connection schema/template changes are backend-only changes.
- Linked connection edits produce the same canonical state regardless of frontend implementation details.
- Connection preview, validation, and generation operate on the same normalized connection state.

## Frontend processing that remains intentionally local

Keep these responsibilities in the frontend:

- canvas routing, snapping, pan/zoom, hit-testing, anchors, and segment editing;
- selection, grouping, clipboard, undo/redo, and drag interactions;
- rendering icons, shapes, UML, visual controls, menus, and dialogs;
- best-effort form feedback based on backend-served schema, without replacing backend validation;
- local UI preferences, pins, recents, onboarding state, and temporary form state;
- browser ZIP download handling.

## Testing strategy

### Backend

- Property-test normalization and diagram-to-architecture conversion.
- Test old-version migrations through save/load and generation endpoints.
- Test catalog/default/name responses against config-model and generator registries.
- Test diagram-based preview and generation against equivalent direct `ArchitectureDescription` requests.
- Verify typed endpoint schemas appear in OpenAPI.

### Frontend

- Mock bootstrap, initialization, save/load, preview, and diagram-generation APIs.
- Assert placement consumes backend-provided name/defaults.
- Assert export sends diagram state and renders backend `422` field errors.
- Preserve geometry, routing, and editor-interaction property tests.

## Migration order

1. Canonical diagram model and normalization.
2. Typed diagram CRUD responses.
3. Bootstrap and resource-initialization APIs.
4. Diagram-to-architecture conversion service and diagram-based generation/preview APIs.
5. Frontend migration to new APIs.
6. Server-primary save/load.
7. Remove duplicated frontend domain logic and deprecate old direct-generation paths after consumers migrate.
