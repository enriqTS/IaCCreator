# Frontend State and Utilities

## Store composition

`frontend/src/store/diagram-store.ts` is only a Zustand composition point. State belongs in focused slices under `store/slices/`:

- `canvas-slice`, `connector-slice`, and `anchoring-slice` own objects, connectors, anchors, and line geometry.
- `clipboard-slice`, `grouping-slice`, and `zorder-slice` own editing operations.
- `history-slice` and `history-support` own undo/redo snapshots.
- `project-slice`, `serialization-slice`, and `persistence-slice` own project state, the active environment scope view, canonical diagram serialization, and server persistence.
- `ui-slice` and `viewport-slice` own tool, selection, overlay, and viewport state.
- `semantic-containment-slice` owns drag target feedback, submits assign/remove/subtree-move intent, and caches backend-resolved effective scopes and inherited values for configuration rendering.

Canvas objects are the active diagram model. Legacy element state is not the model to extend. The serialization contract is in `src/types/serialization.ts`; it includes canvas objects, connector configuration, groups, line anchors/waypoints, and global routing mode.

## Supporting stores

- `editor-domain-store.ts` hydrates service support, schemas, naming rules, and global defaults from `/api/editor-bootstrap`.
- `schema-store.ts` caches backend variable schemas and retains generated `data/bundled-schemas.ts` only as an offline rendering fallback.
- `connection-preview-store.ts` caches backend connection contributions and issues.
- `apigw-config-store.ts` owns API Gateway editing state.
- `naming-store.ts` fetches the backend naming rule used by client validation.
- `layout-preferences-store.ts`, `pinned-objects-store.ts`, `recently-used-store.ts`, and `tour-store.ts` hold persisted UI preferences and onboarding state.
- `toast-store.ts` provides transient notifications.

## Catalog and types

`data/object-catalog.ts` is the frontend catalog boundary. It combines AWS icon entries with shapes, UML, text, and lines, and marks services unsupported when no generator is available. Semantic boundary entries are built dynamically from the backend containment catalog. The backend `ServiceType`, generator registry, and containment catalog remain the domain authority.

`types/diagram.ts` defines canvas objects, tools, visual configuration, geometry, and service-related client types. `types/serialization.ts` defines saved diagram and generation payloads. `types/api.ts`, `types/connection-preview.ts`, and `types/apigw-config.ts` define API-facing data.

## Utilities

- `api-client.ts` centralizes cookie-authenticated requests and structured API errors.
- `export.ts` submits canonical diagram state to `/api/diagrams/generate/zip`.
- `viewport.ts`, `bounds-utils.ts`, `anchor.ts`, and `snap.ts` provide canvas geometry and snapping.
- `semantic-containment.ts` provides overlap-threshold hit testing, deepest-container selection, collapsed-ancestor visibility, descendant traversal, and hierarchy z-order normalization using the backend bootstrap rules.
- `container-layout.ts` deterministically arranges direct children and translates nested subtrees without changing their internal geometry.
- `utils/routing/` contains the grid builder, pathfinder, obstacle collector, and orthogonal-router entry point; `parallel-offset.ts` separates parallel lines.
- `keyboard-shortcuts.ts` centralizes shortcut behavior.
- `name-utils.ts` and `object-search.ts` provide naming and catalog search helpers.
- `safe-storage.ts` wraps browser storage for persisted Zustand stores.

Use these shared utilities and the existing slices rather than adding unrelated behavior to `diagram-store.ts`.
