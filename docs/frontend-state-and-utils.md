# Frontend State & Utilities

Zustand stores, utility modules, and TypeScript type definitions in the frontend.

## Zustand Stores (`frontend/src/store/`)

### `diagram-store.ts` — `useDiagramStore`

The primary application store managing all diagram state. Created with Zustand's `create()`.

**Element State (legacy — kept for backward compatibility):**
- `elements: Map<string, DiagramElement>` — legacy diagram nodes keyed by ID (superseded by `canvasObjects`)
- `addElement(serviceType, position)` — creates a new legacy element with UUID
- `updateElementPosition / updateElementConfig / updateElementName / removeElement`
- Note: All runtime usage now goes through `canvasObjects` with `architecture-block` type. The `elements` map is retained only for serialization backward compatibility.

**Canvas Object State:**
- `canvasObjects: Map<string, CanvasObject>` — all canvas objects (architecture blocks, lines, geometric shapes, text, UML)
- `selectedObjectIds: Set<string>` — multi-selection set
- `addCanvasObject(payload)` — creates a new object with UUID and auto-assigned zIndex
- `updateCanvasObject(id, updates)` — partial update
- `removeCanvasObject(id)` — deletes object and cleans up anchored lines
- `selectObject / toggleObjectSelection / selectObjectsByRect / clearSelection / selectAllObjects`
- `updateVisualConfig(id, config)` — update visual properties (size, color, etc.)
- `updateObjectBounds(id, bounds)` — resize width/height
- `updateLineEndpoint(id, endpoint, position)` — move line start/end point

**Z-Order:**
- `bringToFront / sendToBack / bringForward / sendBackward`

**Grouping:**
- `objectGroups: Map<string, ObjectGroup>` — named groups of objects
- `groupSelectedObjects()` — create a group from selection
- `ungroupObjects(groupId)` — dissolve a group

**Clipboard & Duplicate:**
- `clipboard: CanvasObject[]`
- `copySelectedObjects() / pasteObjects(position) / duplicateSelectedObjects()`

**Lock & Move:**
- `toggleLockObjects(ids)` — toggle lock state on objects
- `moveSelectedObjects(dx, dy)` — batch move all selected objects

**Text Editing:**
- `editingTextId` / `setEditingTextId` / `updateTextContent`

**Anchor Management:**
- `updateLineAnchors(lineId, anchors)` — set source/target anchor refs
- `recomputeAnchoredEndpoints(movedObjectId)` — recalculate line endpoints when an anchored object moves

**Pull-to-Connect:**
- `pullConnectState` / `setPullConnectState` — state for drag-to-connect interaction

**Connector State:**
- `connectors: Map<string, Connector>` — all connectors keyed by ID
- `addConnector / updateConnectorType / removeConnector`

**Viewport State:**
- `viewport: Viewport` — `{offsetX, offsetY, scale}`
- `pan(dx, dy)` / `zoom(factor, center)` — via `zoomAtPoint()`
- `fitToScreen(containerRect)` — auto-fit all objects into view

**UI State:**
- `activeTool: Tool` — current tool (pointer, connector, place-service, place-shape, place-uml, line, text)
- `selectedElementId / selectedConnectorId` — legacy single selection
- `pendingConnectorSourceId` — source element when drawing a connector

**History (Undo/Redo):**
- Snapshot-based history with `MAX_HISTORY = 50` levels
- `undo() / redo()` — restore previous/next snapshot
- `canUndo / canRedo` — boolean flags
- `beginDragGesture()` — capture snapshot before a drag operation
- Snapshots deep-clone `elements`, `connectors`, `canvasObjects`, and `objectGroups` Maps

**Project State:**
- `projectName` / `environments` / `setProjectName` / `setEnvironments`

**Terraform Variables:**
- `setTerraformVariable(objectId, varName, value)` — set a single variable
- `setTerraformVariables(objectId, vars)` — set multiple variables
- `globalTerraformConfig` / `updateGlobalTerraformConfig`

**Serialization:**
- `serializeDiagramState() -> DiagramState` — for save/load
- `loadDiagramState(state)` — restores from a `DiagramState`
- `serializeToArchitectureDescription() -> ArchitectureDescription` — for Terraform export

**Server Persistence:**
- `currentDiagramId / diagramSummaries / isSaving / isLoading`
- `saveDiagramToServer() / updateDiagramOnServer(id) / loadDiagramFromServer(id)`
- `listDiagramsFromServer() / deleteDiagramFromServer(id)`

**Panel State:**
- `bottomPanelExpanded / bottomPanelHeight / toggleBottomPanel`
- `sidebarExpanded / sidebarWidth / setSidebarWidth`

### `toast-store.ts` — `useToastStore`

Simple notification store:
- `toasts: Toast[]` — array of `{id, message, type}`
- `addToast(message, type)` — adds a toast, auto-removes after 4 seconds
- `removeToast(id)` — manual removal

### `layout-preferences-store.ts` — `useLayoutPreferencesStore`

Persisted layout preferences (via Zustand `persist` middleware):
- `sidebarSide: 'left' | 'right'` (default `'right'`)
- `toolbarPosition: 'top' | 'bottom'` (default `'top'`)
- `setSidebarSide / setToolbarPosition`

### `schema-store.ts` — `fetchSchemas` / `getSchemas`

Module-level schema cache (not a Zustand store). Fetches variable schemas from the backend `/api/variable-schemas` endpoint and caches in memory. Falls back to bundled schemas (`frontend/src/data/bundled-schemas.ts`) when the API is unreachable.

- `fetchSchemas()` — async fetch with in-memory caching
- `getSchemas()` — synchronous access to cached or bundled schemas
- `clearSchemaCache()` — reset cache (for testing)

### `recently-used-store.ts` — `useRecentlyUsedStore`

Tracks recently used picker items (via Zustand `persist` middleware with sessionStorage, falling back to in-memory storage when sessionStorage is unavailable):
- `recentItems: PickerItem[]` — capped at `MAX_RECENT_ITEMS` (12)
- `addRecentItem(item)` — prepend item, deduplicate by name+category
- `clearRecentItems()` — reset list

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

All requests include `credentials: 'include'` for cookie-based sessions. Base URL from `NEXT_PUBLIC_API_URL` env var (default empty = relative paths). Pydantic 422 errors are parsed into `fieldErrors`.

### `export.ts`

Export utility for Terraform generation:
- `exportToTerraform(serializeFn, canvasObjects)` — validates non-empty diagram (requires at least one `architecture-block`), checks required config fields (e.g., `hash_key` for DynamoDB), calls `apiClient.generateTerraform()`, triggers browser download of `terraform.zip`
- Returns `ExportResult` with `success`, optional `error`, and optional `fieldErrors`

### `storage.ts`

localStorage-based save/load:
- `saveDiagram(name, state)` — saves under `diagram-editor:{name}`, handles quota exceeded
- `loadDiagram(name)` — loads and validates JSON + version field
- `listSavedDiagrams()` — returns `SavedDiagramEntry[]` with name and savedAt
- `deleteSavedDiagram(name)` — removes from localStorage

### `routing.ts`

Orthogonal connection routing between anchor ports. Computes waypoints for right-angle paths between two anchor positions on objects.

- `computeOrthogonalWaypoints(start, startPosition, end, endPosition, minOffset)` — returns intermediate waypoints (excluding start/end) for an orthogonal route
- Handles five cases: facing anchors (aligned, offset, wrong direction), perpendicular anchors, and same-side anchors (U-shape)
- `MIN_OFFSET` (20px) — minimum distance from the object before the first turn

### `anchor.ts`

Anchor and connection geometry utilities:
- `getAnchorPoints(bounds)` — returns 4 cardinal anchor points (top, right, bottom, left) for a bounding rect
- `computeAnchorPoint(bounds, externalPoint)` — closest point on a rect's edge to an external point
- `rayRectIntersection(rect, target)` — where a ray from rect center to target intersects the rect boundary
- `findSnapAnchor(point, bounds, threshold)` — snap to nearest anchor within threshold (default 20px)

### `shape-paths.ts`

SVG path registry for geometric shapes. `SHAPE_PATH_REGISTRY` maps each `GeometricShape` to a function `(width, height) => string` returning an SVG path `d` attribute. Covers 25+ shapes including basic shapes, polygons, arrows, flowchart shapes, and special shapes (cylinder, cloud, callout).

## Data Modules (`frontend/src/data/`)

| Module                    | Purpose                                                              |
|---------------------------|----------------------------------------------------------------------|
| `bundled-schemas.ts`      | Bundled copy of variable schemas for offline/fallback use            |
| `aws-icon-registry.ts`    | Maps AWS service types to icon components/paths                      |
| `abbreviation-map.ts`     | Maps abbreviations to full service names for search (e.g., "ec2" → "Elastic Compute Cloud") |
| `shape-icons.tsx`         | Icon components for geometric shapes in the picker                   |

## Type Definitions (`frontend/src/types/`)

### `diagram.ts`

### `diagram.ts`

Core diagram types:
- `ServiceType` — union: `'lambda' | 's3' | 'api-gateway' | 'dynamodb' | 'iam' | 'cloudwatch'`
- `Point` — `{x, y}`
- `DiagramElement` — `{id, serviceType, name, position, config}` (legacy, superseded by `ArchitectureBlock`)
- `Connector` — `{id, sourceId, targetId, connectionType}`
- `Viewport` — `{offsetX, offsetY, scale}` (scale range 0.1–5.0)
- `Tool` — `'pointer' | 'connector' | 'line' | 'text' | {type: 'place-service', serviceType} | {type: 'place-shape', shape} | {type: 'place-uml', umlKind}`
- `ResourceConfig` — mirrors the backend's `ResourceConfig` Pydantic schema
- `EnvironmentConfig` — `{name, variables}`
- `CanvasObjectType` — `'architecture-block' | 'line' | 'geometric' | 'text' | 'uml'`
- `CanvasObject` — discriminated union of `ArchitectureBlock | LineObject | GeometricObject | TextObject | UMLObject`
- `GeometricShape` — 25+ shape types (rectangle, ellipse, diamond, hexagon, star, cloud, flowchart shapes, etc.)
- `UMLKind` — `'class' | 'interface' | 'actor' | 'use-case' | 'component' | 'package' | 'node'`
- Visual config interfaces: `ArchitectureBlockVisualConfig`, `LineVisualConfig`, `GeometricVisualConfig`, `TextVisualConfig`, `UMLVisualConfig`
- `ObjectGroup` — `{id, name, memberIds}`
- `AnchorRef` — `{objectId}` for line anchoring
- `Rect` — `{x, y, width, height}` axis-aligned bounding box
- `getObjectBounds(obj)` — compute bounding box for any canvas object
- Default visual configs: `DEFAULT_BLOCK_VISUAL`, `DEFAULT_LINE_VISUAL`, `DEFAULT_GEO_VISUAL`, `DEFAULT_TEXT_VISUAL`, `DEFAULT_UML_VISUAL`

### `serialization.ts`

Serialization types:
- `CURRENT_DIAGRAM_VERSION = 3`
- `DiagramState` — full state for save/load: `version`, `projectName`, `environments`, `elements`, `canvasObjects`, `connectors`, `viewport`, `objectGroups`, `globalTerraformConfig`
- `SerializedElement` / `SerializedCanvasObject` / `SerializedConnector` / `SerializedObjectGroup`
- `ArchitectureDescription` — maps to the backend's Pydantic schema for Terraform export

### `terraform-variables.ts`

Terraform variable schemas and global configuration:
- `VARIABLE_SCHEMAS` — per-service variable definitions (name, type, description, default)
- `GlobalTerraformConfig` — backend, provider, version constraints, environments, global variables
- `DEFAULT_GLOBAL_CONFIG` — sensible defaults (local backend, us-east-1)
- `getDefaultVariables(serviceType)` — returns default variable values for a service type

### `api.ts`

API response types:
- `DiagramSummary` — `{diagram_id, project_name, updated_at}`
- `ApiError` — `{type: 'network' | 'http', status?, message, fieldErrors?}`
- `ApiResult<T>` — discriminated union: `{ok: true, data: T} | {ok: false, error: ApiError}`
