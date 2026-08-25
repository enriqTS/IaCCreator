# Canvas UX Work Record

This document records the canvas UX work that originated as an implementation plan. It is not a current roadmap.

## Completed routing work

The obstacle-aware orthogonal router is implemented under `frontend/src/utils/routing/`:

- `routing-grid.ts` builds routing coordinates from objects and margins.
- `routing-pathfinder.ts` finds paths through the grid.
- `routing-obstacles.ts` converts canvas objects to obstacles.
- `orthogonal-router.ts` is the router entry point.
- `routing.ts` retains deterministic routing/fallback behavior.

The canvas line renderer, pull-to-connect preview, and segment handles use the routing implementation. Routing has unit tests for the grid, pathfinder, router, and phase-two behavior, plus property tests for anchors, exits, orthogonal segments, snapping, waypoints, and segment dragging.

## Completed UX work

The project also now has a minimap (`canvas/Minimap.tsx`) and centralized keyboard shortcuts (`utils/keyboard-shortcuts.ts` with `shortcuts/KeyboardShortcutsOverlay.tsx`).

## Follow-up work

Treat future UX ideas as new scoped work rather than unchecked items from the old phased plan. Before changing routing, preserve manual-waypoint behavior, the deterministic fallback, and the geometry/property-test coverage.
