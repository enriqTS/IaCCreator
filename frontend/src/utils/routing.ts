import type { Point } from '@/types/diagram';
import type { AnchorPosition } from '@/utils/anchor';
import { snapToGrid } from '@/utils/snap';

/** Minimum offset distance from the object before the first turn */
export const MIN_OFFSET = 20;

/**
 * Infer an anchor exit direction from one point toward another.
 * Used for unanchored endpoints to determine orthogonal routing direction.
 *
 * - If |dx| >= |dy|: returns 'right' (dx > 0) or 'left' (dx < 0)
 * - If |dy| > |dx|: returns 'bottom' (dy > 0) or 'top' (dy < 0)
 * - When both dx and dy are 0, returns 'right' as default.
 */
export function inferAnchorPosition(from: Point, to: Point): AnchorPosition {
  const dx = to.x - from.x;
  const dy = to.y - from.y;

  if (dx === 0 && dy === 0) {
    return 'right';
  }

  if (Math.abs(dx) >= Math.abs(dy)) {
    return dx > 0 ? 'right' : 'left';
  }

  return dy > 0 ? 'bottom' : 'top';
}

/**
 * Get the unit direction vector for an anchor position's outward-facing direction.
 * top → (0, -1), right → (1, 0), bottom → (0, 1), left → (-1, 0)
 */
function getDirection(position: AnchorPosition): Point {
  switch (position) {
    case 'top': return { x: 0, y: -1 };
    case 'right': return { x: 1, y: 0 };
    case 'bottom': return { x: 0, y: 1 };
    case 'left': return { x: -1, y: 0 };
  }
}

/** Check if an anchor exits horizontally (right or left) */
function isHorizontal(position: AnchorPosition): boolean {
  return position === 'right' || position === 'left';
}

/** Get the opposite anchor position */
function opposite(position: AnchorPosition): AnchorPosition {
  switch (position) {
    case 'top': return 'bottom';
    case 'bottom': return 'top';
    case 'left': return 'right';
    case 'right': return 'left';
  }
}

/**
 * Compute waypoints for an orthogonal route between two anchor ports.
 * Returns an array of intermediate points (excluding start and end).
 * The path exits each anchor perpendicular to its side for at least minOffset pixels.
 *
 * When `gridSize` is provided, all computed waypoint coordinates are snapped to the grid
 * and `gridSize` is used as the `minOffset` value.
 */
export function computeOrthogonalWaypoints(
  start: Point,
  startPosition: AnchorPosition,
  end: Point,
  endPosition: AnchorPosition,
  minOffset: number = MIN_OFFSET,
  gridSize?: number,
): Point[] {
  // When gridSize is provided, use it as minOffset
  const effectiveMinOffset = gridSize && gridSize > 0 ? gridSize : minOffset;

  // Helper to snap waypoints when gridSize is provided
  const snapWaypoints = (waypoints: Point[]): Point[] => {
    if (!gridSize || gridSize <= 0) return waypoints;
    return waypoints.map(p => ({
      x: snapToGrid(p.x, gridSize),
      y: snapToGrid(p.y, gridSize),
    }));
  };

  // Degenerate case: start and end are the same point
  if (start.x === end.x && start.y === end.y) {
    return [];
  }

  const startDir = getDirection(startPosition);
  const endDir = getDirection(endPosition);

  // Compute exit points: extend effectiveMinOffset pixels in the outward direction
  const startExit: Point = {
    x: start.x + startDir.x * effectiveMinOffset,
    y: start.y + startDir.y * effectiveMinOffset,
  };
  const endExit: Point = {
    x: end.x + endDir.x * effectiveMinOffset,
    y: end.y + endDir.y * effectiveMinOffset,
  };

  const startH = isHorizontal(startPosition);
  const endH = isHorizontal(endPosition);

  let waypoints: Point[];

  // Facing anchors (opposite directions)
  if (endPosition === opposite(startPosition)) {
    if (startH) {
      // Both exit horizontally in opposite directions
      const facingCorrectly = startDir.x * (end.x - start.x) > 0;

      if (facingCorrectly && start.y === end.y) {
        // Case 1: Facing, aligned — zero waypoints
        return [];
      }

      if (facingCorrectly) {
        const midX = (startExit.x + endExit.x) / 2;
        const startOk = startDir.x > 0 ? midX >= startExit.x : midX <= startExit.x;
        const endOk = endDir.x > 0 ? midX >= endExit.x : midX <= endExit.x;

        if (startOk && endOk) {
          waypoints = [
            { x: midX, y: start.y },
            { x: midX, y: end.y },
          ];
        } else {
          // Too close for S-shape — fall back to detour using exit points
          const midY = (start.y + end.y) / 2;
          waypoints = [
            startExit,
            { x: startExit.x, y: midY },
            { x: endExit.x, y: midY },
            endExit,
          ];
        }
      } else {
        // Case 5: Opposing, wrong direction — detour
        // Exit both sides, route around via midY
        const midY = (start.y + end.y) / 2;
        waypoints = [
          startExit,
          { x: startExit.x, y: midY },
          { x: endExit.x, y: midY },
          endExit,
        ];
      }
    } else {
      // Both exit vertically in opposite directions
      const facingCorrectly = startDir.y * (end.y - start.y) > 0;

      if (facingCorrectly && start.x === end.x) {
        // Case 1: Facing, aligned — zero waypoints
        return [];
      }

      if (facingCorrectly) {
        const midY = (startExit.y + endExit.y) / 2;
        const startOk = startDir.y > 0 ? midY >= startExit.y : midY <= startExit.y;
        const endOk = endDir.y > 0 ? midY >= endExit.y : midY <= endExit.y;

        if (startOk && endOk) {
          waypoints = [
            { x: start.x, y: midY },
            { x: end.x, y: midY },
          ];
        } else {
          // Too close for S-shape — fall back to detour using exit points
          const midX = (start.x + end.x) / 2;
          waypoints = [
            startExit,
            { x: midX, y: startExit.y },
            { x: midX, y: endExit.y },
            endExit,
          ];
        }
      } else {
        // Case 5: Opposing, wrong direction — detour
        const midX = (start.x + end.x) / 2;
        waypoints = [
          startExit,
          { x: midX, y: startExit.y },
          { x: midX, y: endExit.y },
          endExit,
        ];
      }
    }
  } else if (startH !== endH) {
    // Case 3: Perpendicular anchors — one exits H, the other V
    if (startH) {
      // Start exits horizontally, end exits vertically
      // Natural corner at (end.x, start.y)
      const corner: Point = { x: end.x, y: start.y };
      const startOk = startDir.x * (corner.x - start.x) >= effectiveMinOffset;
      const endOk = endDir.y * (corner.y - end.y) >= effectiveMinOffset;

      if (startOk && endOk) {
        waypoints = [corner];
      } else {
        // Fallback: use exit points and route through them
        waypoints = [
          startExit,
          { x: endExit.x, y: startExit.y },
          endExit,
        ];
      }
    } else {
      // Start exits vertically, end exits horizontally
      // Natural corner at (start.x, end.y)
      const corner: Point = { x: start.x, y: end.y };
      const startOk = startDir.y * (corner.y - start.y) >= effectiveMinOffset;
      const endOk = endDir.x * (corner.x - end.x) >= effectiveMinOffset;

      if (startOk && endOk) {
        waypoints = [corner];
      } else {
        waypoints = [
          startExit,
          { x: startExit.x, y: endExit.y },
          endExit,
        ];
      }
    }
  } else if (startH) {
    // Case 4: Same-side anchors — U-shape (horizontal)
    const outX = startDir.x > 0
      ? Math.max(startExit.x, endExit.x)
      : Math.min(startExit.x, endExit.x);
    waypoints = [
      { x: outX, y: start.y },
      { x: outX, y: end.y },
    ];
  } else {
    // Case 4: Same-side anchors — U-shape (vertical)
    const outY = startDir.y > 0
      ? Math.max(startExit.y, endExit.y)
      : Math.min(startExit.y, endExit.y);
    waypoints = [
      { x: start.x, y: outY },
      { x: end.x, y: outY },
    ];
  }

  return snapWaypoints(waypoints);
}
