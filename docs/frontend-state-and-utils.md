# Frontend State and Utilities

## Store composition

`frontend/src/store/diagram-store.ts` is only a Zustand composition point. State belongs in focused slices under `store/slices/`:

- `canvas-slice`, `connector-slice`, and `anchoring-slice` own objects, connectors, anchors, and line geometry.
- `clipboard-slice`, `grouping-slice`, and `zorder-slice` own editing operations.
- `history-slice` and `history-support` own undo/redo snapshots.
- `project-slice`, `serialization-slice`, and `persistence-slice` own project state, API/local persistence, and architecture export.
- `ui-slice` and `viewport-slice` own tool, selection, overlay, and viewport state.

Canvas objects are the active diagram model. Legacy element state is not the model to extend. The serialization contract is in `src/types/serialization.ts`; it includes canvas objects, connector configuration, groups, line anchors/waypoints, and global routing mode.

## Supporting stores

- `schema-store.ts` fetches backend variable schemas and falls back to generated `data/bundled-schemas.ts`.
- `connection-preview-store.ts` caches backend connection contributions and issues.
- `apigw-config-store.ts` owns API Gateway editing state.
- `naming-store.ts` fetches the backend naming rule used by client validation.
- `layout-preferences-store.ts`, `pinned-objects-store.ts`, `recently-used-store.ts`, and `tour-store.ts` hold persisted UI preferences and onboarding state.
- `toast-store.ts` provides transient notifications.

## Catalog and types

`data/object-catalog.ts` is the frontend catalog boundary. It combines AWS icon entries with shapes, UML, text, and lines, and marks services unsupported when no generator is available. The backend `ServiceType` and generator registry remain the domain authority.

`types/diagram.ts` defines canvas objects, tools, visual configuration, geometry, and service-related client types. `types/serialization.ts` defines saved diagram and generation payloads. `types/api.ts`, `types/connection-preview.ts`, and `types/apigw-config.ts` define API-facing data.

## Utilities

- `api-client.ts` centralizes cookie-authenticated requests and structured API errors.
- `export.ts` submits serialized architecture to `/generate/zip`.
- `viewport.ts`, `bounds-utils.ts`, `anchor.ts`, and `snap.ts` provide canvas geometry and snapping.
- `utils/routing/` contains the grid builder, pathfinder, obstacle collector, and orthogonal-router entry point; `parallel-offset.ts` separates parallel lines.
- `keyboard-shortcuts.ts` centralizes shortcut behavior.
- `name-utils.ts` and `object-search.ts` provide naming and catalog search helpers.
- `safe-storage.ts` wraps browser storage for persisted Zustand stores.

Use these shared utilities and the existing slices rather than adding unrelated behavior to `diagram-store.ts`.
