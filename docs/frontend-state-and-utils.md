# Frontend State & Utilities

Zustand stores, utility modules, and TypeScript type definitions in the frontend.

## Zustand Stores (`frontend/src/store/`)

### `diagram-store.ts` — `useDiagramStore`

The primary application store managing all diagram state. Created with Zustand's `create()`.

**Element State:**
- `elements: Map<string, DiagramElement>` — all diagram nodes keyed by ID
- `addElement(serviceType, position)` — creates a new element with UUID, returns the ID
- `updateElementPosition(id, position)` — moves an element
- `updateElementConfig(id, config)` — merges partial config into an element
- `updateElementName(id, name)` — renames an element
- `removeElement(id)` — deletes an element and its connected connectors

**Connector State:**
- `connectors: Map<string, Connector>` — all connectors keyed by ID
- `addConnector(sourceId, targetId, connectionType?)` — creates a connector
- `updateConnectorType(id, connectionType)` — changes the connection type
- `removeConnector(id)` — deletes a connector

**Viewport State:**
- `viewport: Viewport` — `{offsetX, offsetY, scale}`
- `pan(dx, dy)` — translates the viewport
- `zoom(factor, center)` — zooms at a screen point via `zoomAtPoint()`

**UI State:**
- `activeTool: Tool` — current tool (`'pointer'`, `'connector'`, or `{type: 'place-service', serviceType}`)
- `selectedElementId / selectedConnectorId` — current selection
- `pendingConnectorSourceId` — source element when drawing a connector

**History (Undo/Redo):**
- Snapshot-based history with `MAX_HISTORY = 50` levels
- `undo()` / `redo()` — restore previous/next snapshot
- `canUndo` / `canRedo` — boolean flags
- Snapshots deep-clone `elements` and `connectors` Maps

**Project State:**
- `projectName: string`
- `environments: EnvironmentConfig[]`
- `setProjectName(name)` / `setEnvironments(envs)`

**Serialization:**
- `serializeDiagramState() -> DiagramState` — for save/load
- `loadDiagramState(state)` — restores from a `DiagramState`
- `serializeToArchitectureDescription() -> ArchitectureDescription` — for Terraform export

**Server Persistence:**
- `currentDiagramId` / `diagramSummaries` / `isSaving` / `isLoading`
- `saveDiagramToServer()` / `updateDiagramOnServer(id)` / `loadDiagramFromServer(id)`
- `listDiagramsFromServer()` / `deleteDiagramFromServer(id)`

### `toast-store.ts` — `useToastStore`

Simple notification store:
- `toasts: Toast[]` — array of `{id, message, type}`
- `addToast(message, type)` — adds a toast, auto-removes after 4 seconds
- `removeToast(id)` — manual removal

## Utilities (`frontend/src/utils/`)

### `viewport.ts`

Viewport math functions:
- `clamp(value, min, max)` — clamp a number
- `screenToCanvas(screenPoint, viewport)` — convert screen pixels to canvas world coordinates
- `canvasToScreen(canvasPoint, viewport)` — convert canvas world to screen pixels
- `zoomAtPoint(viewport, factor, screenCenter)` — zoom keeping the cursor point fixed, scale clamped to `[0.1, 5.0]`

### `api-client.ts`

Centralized API client. Every method returns `ApiResult<T>` (discriminated union: `{ok: true, data}` or `{ok: false, error}`).

Methods:
- `saveDiagram(state)` — `POST /api/diagrams`
- `updateDiagram(id, state)` — `PUT /api/diagrams/{id}`
- `listDiagrams()` — `GET /api/diagrams`
- `loadDiagram(id)` — `GET /api/diagrams/{id}`
- `deleteDiagram(id)` — `DELETE /api/diagrams/{id}`
- `generateTerraform(arch)` — `POST /generate/zip` (returns `Blob`)

All requests include `credentials: 'include'` for cookie-based sessions. Pydantic 422 errors are parsed into `fieldErrors`.

### `export.ts`

Export utility for Terraform generation:
- `exportToTerraform(serializeFn, elements)` — validates non-empty diagram, checks required config fields (e.g., `hash_key` for DynamoDB), calls `apiClient.generateTerraform()`, triggers browser download of `terraform.zip`
- Returns `ExportResult` with `success`, optional `error`, and optional `fieldErrors`

### `storage.ts`

localStorage-based save/load:
- `saveDiagram(name, state)` — saves under `diagram-editor:{name}`, handles quota exceeded
- `loadDiagram(name)` — loads and validates JSON + version field
- `listSavedDiagrams()` — returns `SavedDiagramEntry[]` with name and savedAt
- `deleteSavedDiagram(name)` — removes from localStorage

## Type Definitions (`frontend/src/types/`)

### `diagram.ts`

Core diagram types:
- `ServiceType` — union: `'lambda' | 's3' | 'api-gateway' | 'dynamodb' | 'iam' | 'cloudwatch'`
- `Point` — `{x, y}`
- `DiagramElement` — `{id, serviceType, name, position, config}`
- `Connector` — `{id, sourceId, targetId, connectionType}`
- `Viewport` — `{offsetX, offsetY, scale}` (scale range 0.1–5.0)
- `Tool` — `'pointer' | 'connector' | {type: 'place-service', serviceType}`
- `ResourceConfig` — mirrors the backend's `ResourceConfig` Pydantic schema
- `EnvironmentConfig` — `{name, variables}`

### `serialization.ts`

Serialization types:
- `DiagramState` — full state for save/load: `version`, `projectName`, `environments`, `elements`, `connectors`, `viewport`
- `SerializedElement` / `SerializedConnector` — flattened element/connector shapes
- `ArchitectureDescription` — maps to the backend's Pydantic schema for Terraform export

### `api.ts`

API response types:
- `DiagramSummary` — `{diagram_id, project_name, updated_at}`
- `ApiError` — `{type: 'network' | 'http', status?, message, fieldErrors?}`
- `ApiResult<T>` — discriminated union: `{ok: true, data: T} | {ok: false, error: ApiError}`
