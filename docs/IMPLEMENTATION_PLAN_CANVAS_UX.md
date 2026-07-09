# Implementation Plan: Canvas UX Overhaul

## Overview

This plan covers two major areas:
1. **Connector Routing Overhaul** (Phases 1 & 2) — the primary focus
2. **General UX Improvements** — secondary, to be tackled after routing is solid

---

## Part 1: Connector Routing Overhaul

### Current State

The current routing (`utils/routing.ts`) uses a deterministic, case-based geometric algorithm:
- Takes only `start`, `startPosition`, `end`, `endPosition` as inputs
- Has no awareness of other objects on the canvas (no obstacle avoidance)
- Produces fixed topologies: S-shape for facing anchors, single corner for perpendicular, U-shape for same-side
- Works well for simple 2-node connections but breaks down with intermediate objects

**Call sites:**
- `LineObjectComponent.tsx` — computes path for rendering (in `useMemo`)
- `PullToConnectOverlay.tsx` — live preview during connection drag
- `ElementLayer.tsx` — computes `selectedLinePathPoints` for SegmentHandles
- Property tests — validate grid alignment and offset rules

**Re-routing trigger:** `recomputeAnchoredEndpoints()` is called after `moveSelectedObjects()`. It re-evaluates anchor positions and updates start/end points, but does NOT recompute intermediate waypoints.

### Target State

A grid-based pathfinding router that:
- Considers all canvas objects as potential obstacles
- Finds the shortest orthogonal path that avoids all obstacles
- Minimizes bends (fewer turns = cleaner diagrams)
- Produces balanced, aesthetically pleasing routes
- Supports user waypoint overrides (preserving existing SegmentHandles behavior)
- Performs well enough for real-time re-routing during drag (target: <5ms for 50 objects)

---

### Phase 1: Grid-Based Dijkstra Router with Obstacle Avoidance

**Goal:** Replace the core routing algorithm with a visibility-graph-based Dijkstra router that avoids obstacles.

**Reference implementations:**
- jose-mdz Orthogonal Connector Router (TypeScript, ~400 LOC, MIT) — https://gist.github.com/jose-mdz/4a8894c152383b9d7a870c24a04447e4
- Bukk94/OrthogonalConnectorRouting (C#, Dijkstra on ruler-projected grid)
- draw.io/mxGraph `mxEdgeStyle` (visibility graph approach)
- elbow-links formalization — https://elbow-links.onrender.com/

#### Task 1.1: Create the Grid Builder (`utils/routing-grid.ts`)

**Purpose:** Convert the canvas state into a routing grid.

**Algorithm:**
1. Accept inputs: source rect, target rect, all obstacle rects, shape margin (padding around shapes)
2. Inflate all obstacle rects by `shapeMargin` on each side
3. If inflated source and target rects overlap, reduce margin to 0 (graceful degradation for close shapes)
4. Project horizontal rulers from top/bottom edges of all inflated shapes
5. Project vertical rulers from left/right edges of all inflated shapes
6. Add rulers at the source/target connection points (anchor exit positions)
7. Compute a bounding box: union of inflated source + target + all obstacles, then inflate by a global margin
8. Build a grid of rectangles from ruler intersections within the bounds
9. Generate candidate "spots" (routing nodes) from grid cell corners, edges, and centers
10. Filter out spots that fall inside any inflated obstacle rect

**Outputs:** Array of valid routing points (spots)

**Key types:**
```typescript
interface RoutingRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface RoutingRequest {
  sourcePoint: Point;
  sourceSide: AnchorPosition;
  sourceRect: RoutingRect;
  targetPoint: Point;
  targetSide: AnchorPosition;
  targetRect: RoutingRect;
  obstacles: RoutingRect[];
  shapeMargin: number;  // default: 20 (matches current MIN_OFFSET)
}

interface RoutingResult {
  waypoints: Point[];  // Intermediate points (excludes start/end)
  success: boolean;
}
```

#### Task 1.2: Create the Graph & Dijkstra Solver (`utils/routing-pathfinder.ts`)

**Purpose:** Build a graph from spots and find the shortest path with bend penalty.

**Algorithm:**
1. Collect all unique X and Y coordinates from spots
2. Sort them to form a grid index
3. For each spot, find nearest horizontal neighbor (same Y, next X) and nearest vertical neighbor (same X, next Y) — connect bidirectionally
4. Edge weight = Euclidean distance between connected spots
5. **Bend penalty:** When evaluating a neighbor node `B` from current node `A`, look at the path direction arriving at `A`. If reaching `B` requires a direction change (H→V or V→H), add extra cost: `extraWeight = (edgeWeight + 1)²`. This strongly favors continuing straight.
6. Run Dijkstra's algorithm from source exit point to target exit point, using a priority queue (sorted array or binary heap)
7. Extract path by backtracking from destination through `shortestPath` linked list

**Path simplification:** Remove intermediate points that are collinear with their neighbors:
```typescript
function simplifyPath(points: Point[]): Point[] {
  if (points.length <= 2) return points;
  const result = [points[0]];
  for (let i = 1; i < points.length - 1; i++) {
    const prev = points[i - 1], curr = points[i], next = points[i + 1];
    const sameX = prev.x === curr.x && curr.x === next.x;
    const sameY = prev.y === curr.y && curr.y === next.y;
    if (!sameX && !sameY) result.push(curr);
  }
  result.push(points[points.length - 1]);
  return result;
}
```

#### Task 1.3: Create the Router Entry Point (`utils/orthogonal-router.ts`)

**Purpose:** Orchestrate grid building + pathfinding into a single function.

**New function signature:**
```typescript
export function routeOrthogonalConnector(request: RoutingRequest): RoutingResult;
```

**Logic:**
1. Compute source exit point: extrude `shapeMargin` from sourcePoint in sourceSide direction
2. Compute target exit point: extrude `shapeMargin` from targetPoint in targetSide direction
3. Build the grid (Task 1.1) — pass source exit + target exit as additional required spots
4. Build the graph and run pathfinding (Task 1.2) from source exit → target exit
5. If path found: prepend `sourcePoint`, append `targetPoint`, simplify, extract waypoints (middle points only)
6. **Fallback:** If pathfinding fails (no path found), call the old `computeOrthogonalWaypoints` as graceful degradation
7. **Grid snap:** If `gridSize` is provided, snap all computed waypoints to grid

#### Task 1.4: Integration Helper — Obstacle Collection (`utils/routing-obstacles.ts`)

**Purpose:** Centralize the logic for converting canvas objects into obstacle rects.

```typescript
export function collectObstacles(
  canvasObjects: Map<string, CanvasObject>,
  excludeIds: Set<string>,  // source object, target object, the line itself
): RoutingRect[] {
  const obstacles: RoutingRect[] = [];
  for (const [id, obj] of canvasObjects) {
    if (excludeIds.has(id)) continue;
    if (obj.objectType === 'line') continue;  // lines are not obstacles
    const bounds = getObjectBounds(obj);
    obstacles.push({
      left: bounds.x,
      top: bounds.y,
      width: bounds.width,
      height: bounds.height,
    });
  }
  return obstacles;
}
```

#### Task 1.5: Integrate into `LineObjectComponent.tsx`

**Changes to the `pathPoints` useMemo:**

```typescript
// Current:
const waypoints = computeOrthogonalWaypoints(start, startPos, end, endPos, ...);

// New:
const sourceObjId = line.sourceAnchor?.objectId;
const targetObjId = line.targetAnchor?.objectId;
const excludeIds = new Set([line.id, sourceObjId, targetObjId].filter(Boolean));
const obstacles = collectObstacles(canvasObjects, excludeIds);

const sourceRect = sourceObjId
  ? boundsToRoutingRect(getObjectBounds(canvasObjects.get(sourceObjId)!))
  : { left: startPt.x - 1, top: startPt.y - 1, width: 2, height: 2 };

const targetRect = targetObjId
  ? boundsToRoutingRect(getObjectBounds(canvasObjects.get(targetObjId)!))
  : { left: endPt.x - 1, top: endPt.y - 1, width: 2, height: 2 };

const result = routeOrthogonalConnector({
  sourcePoint: effectiveStart,
  sourceSide: startPos,
  sourceRect,
  targetPoint: effectiveEnd,
  targetSide: endPos,
  targetRect,
  obstacles,
  shapeMargin: snapToGridEnabled ? gridCellSize : 20,
});

return [effectiveStart, ...result.waypoints, effectiveEnd];
```

**Note:** `canvasObjects` is already subscribed. Adding obstacles as a useMemo dependency means recomputation when any object changes — correct behavior.

#### Task 1.6: Integrate into `PullToConnectOverlay.tsx`

- Replace `computeOrthogonalWaypoints` with `routeOrthogonalConnector`
- Target during drag: mouse position with minimal 2×2 rect
- Pass all canvas objects (except source) as obstacles
- Performance: if slow, limit obstacles to nearby objects

#### Task 1.7: Integrate into `ElementLayer.tsx`

- Replace `computeOrthogonalWaypoints` in `selectedLinePathPoints` computation
- Must match rendered path exactly (SegmentHandles uses this)

#### Task 1.8: Clear User Waypoints on Object Move

**Changes to `recomputeAnchoredEndpoints` in `diagram-store.ts`:**

```typescript
if (updated) {
  // Clear manual waypoints — geometry changed, route needs recomputation
  updatedLine.waypoints = null;
}
```

**Exception for group moves:** If both source and target objects are in the moved set, translate waypoints instead of clearing:
```typescript
if (line.waypoints && sourceMoving && targetMoving) {
  updatedLine.waypoints = line.waypoints.map(wp => ({
    x: wp.x + dx, y: wp.y + dy
  }));
} else {
  updatedLine.waypoints = null;
}
```

#### Task 1.9: Handle Edge Cases

1. **Overlapping shapes:** Inflated source/target overlap → reduce margin to 0
2. **Self-connections:** Same source and target object → fixed U-shaped detour
3. **No obstacles:** Router produces clean results same as simple case
4. **Free-floating lines:** No anchors → minimal rects, skip obstacle avoidance
5. **Large diagrams (50+ shapes):** Limit obstacles to those within 2× source-target distance

#### Task 1.10: Update Tests

- Existing tests calling `computeOrthogonalWaypoints` remain unchanged (function preserved)
- New tests for `routeOrthogonalConnector`:
  - No obstacles: valid orthogonal path
  - Single obstacle: route avoids it
  - Multiple obstacles: route avoids all
  - Blocked path: fallback triggers
  - Grid snap: waypoints align to grid
  - Performance: 50 obstacles < 10ms

---

### Phase 2: Aesthetic Heuristics & Polish

#### Task 2.1: Balanced Segment Lengths

Post-processing after pathfinding:
- Identify S-shaped routes (2 turns)
- Move middle segment to center of available range between shapes
- For complex routes, minimize maximum segment length

Add: `balancePath(points, sourceRect, targetRect): Point[]`

#### Task 2.2: Improved Anchor Auto-Selection ("Heading" approach)

Replace `findNearestAnchorPosition` with heading-based calculation:
```typescript
export function computeOptimalExitSide(sourceBounds: Rect, targetCenter: Point): AnchorPosition {
  const cx = sourceBounds.x + sourceBounds.width / 2;
  const cy = sourceBounds.y + sourceBounds.height / 2;
  const dx = targetCenter.x - cx;
  const dy = targetCenter.y - cy;
  if (Math.abs(dx) >= Math.abs(dy)) return dx >= 0 ? 'right' : 'left';
  return dy >= 0 ? 'bottom' : 'top';
}
```

Use in `recomputeAnchoredEndpoints` for auto-selection (not user-pinned anchors).

#### Task 2.3: Short-Distance Special Cases

Before invoking full router, check:
- Manhattan distance < 2 × shapeMargin AND shapes don't overlap:
  - Facing anchors: 0 waypoints
  - Perpendicular: 1 waypoint (single corner)
  - Same-side: minimal U-shape with reduced offset

#### Task 2.4: Backward Visit Prevention

In graph construction for source/target exit points:
- Source exit: only connect to neighbors in compatible directions (not 180° opposite of exit)
- Target exit: only reachable from directions compatible with target side
- Only applies to first/last hop; intermediate nodes unconstrained

#### Task 2.5: Parallel Connector Offset

Rendering-level adjustment:
- Detect multiple lines between same object pair
- Assign index per parallel line
- Offset rendered path by `index × 8px` perpendicular to segments
- Stored waypoints unchanged

#### Task 2.6: Performance Optimization (if needed)

Only implement if frame drops observed:
1. Spatial filtering (limit obstacles by proximity)
2. Route caching (memoize by endpoint + obstacle hash)
3. Throttled preview (32ms during drag)
4. Binary heap for Dijkstra priority queue

---

## Part 2: General UX Improvements (from Excalidraw)

*To be tackled after routing is stable.*

### Task 3.1: Keyboard Shortcuts System
- Centralized shortcut registry with help overlay (`?` key)
- Core shortcuts: Ctrl+Z/Y, Ctrl+C/V/X/D, Ctrl+A, Ctrl+G, brackets for z-order, number keys for tools
- Effort: 2-3 days

### Task 3.2: Distribution Snap (Equal Spacing)
- Extend snap.ts with equal-gap detection between 3+ objects
- Show spacing indicators during drag
- Effort: 3-4 days

### Task 3.3: Smooth Zoom Animation
- `requestAnimationFrame` + easing for zoom-to-fit, zoom-to-selection
- Effort: 1 day

### Task 3.4: Switch to PointerEvents
- Replace Mouse events with Pointer events (touch-ready)
- Effort: 0.5-1 day

### Task 3.5: Connector Midpoint Labels Enhancement
- Draggable label offset, double-click to edit
- Effort: 2-3 days

### Task 3.6: Minimap
- Small overview panel with draggable viewport rectangle
- Effort: 3-4 days

### Task 3.7: Cursor Feedback
- Context-appropriate cursors (grab, move, crosshair, resize)
- Effort: 0.5 day

---

## Implementation Order

```
Week 1-2:  Phase 1 Tasks 1.1 → 1.7 (Core router + integration)
Week 2-3:  Phase 1 Tasks 1.8 → 1.10 (Edge cases + tests)
Week 3-4:  Phase 2 Tasks 2.1 → 2.4 (Aesthetic heuristics)
Week 4:    Phase 2 Tasks 2.5 → 2.6 (Parallel offset + performance)
Week 5:    Task 3.1 (Keyboard shortcuts)
Week 5-6:  Task 3.2 (Distribution snap)
Week 6:    Tasks 3.3, 3.4 (Zoom animation, PointerEvents)
Week 7:    Tasks 3.5, 3.6, 3.7 (Labels, minimap, cursors)
```

## Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/utils/routing-grid.ts` | Grid builder from shape rulers |
| `frontend/src/utils/routing-pathfinder.ts` | Graph construction + Dijkstra |
| `frontend/src/utils/orthogonal-router.ts` | Entry point orchestrator |
| `frontend/src/utils/routing-obstacles.ts` | Canvas objects → obstacle rects |
| `frontend/src/utils/keyboard-shortcuts.ts` | Shortcut manager (Part 2) |

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/utils/routing.ts` | Keep as fallback, mark deprecated |
| `frontend/src/components/canvas/LineObjectComponent.tsx` | Use new router |
| `frontend/src/components/canvas/PullToConnectOverlay.tsx` | Use new router |
| `frontend/src/components/canvas/ElementLayer.tsx` | Use new router for path computation |
| `frontend/src/store/diagram-store.ts` | Clear waypoints on move, add shortcut actions |
| `frontend/src/utils/snap.ts` | Add distribution detection (Part 2) |
| `frontend/src/utils/viewport.ts` | Add animated zoom (Part 2) |
| `frontend/src/hooks/useSnapDrag.ts` | Add distribution guides (Part 2) |
| `frontend/src/components/canvas/Canvas.tsx` | PointerEvents migration (Part 2) |

## Risk Mitigations

1. **Regression risk:** Keep `computeOrthogonalWaypoints` as fallback. If new router returns `success: false`, degrade gracefully to old algorithm.
2. **Performance risk:** Grid router in useMemo per line. For 20 lines × 50 obstacles = ~40ms worst case. If too slow, move to store-level batch computation or spatial filtering.
3. **Test stability:** Existing property tests call old function directly — unchanged. New tests cover router independently.
4. **User waypoint preservation:** Never overwrite `line.waypoints` during rendering. Only clear from store actions (object move, anchor switch).
5. **Feature flag:** Consider a `useNewRouter` toggle in layout preferences for quick rollback.
