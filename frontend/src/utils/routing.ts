import type { Point } from '@/types/diagram';
import type { AnchorPosition } from '@/utils/anchor';

/** Minimum offset distance from the object before the first turn */
export const MIN_OFFSET = 20;

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
 */
export function computeOrthogonalWaypoints(
  start: Point,
  startPosition: AnchorPosition,
  end: Point,
  endPosition: AnchorPosition,
  minOffset: number = MIN_OFFSET,
): Point[] {
  // Degenerate case: start and end are the same point
  if (start.x === end.x && start.y === end.y) {
    return [];
  }

  const startDir = getDirection(startPosition);
  const endDir = getDirection(endPosition);

  // Compute exit points: extend minOffset pixels in the outward direction
  const startExit: Point = {
    x: start.x + startDir.x * minOffset,
    y: start.y + startDir.y * minOffset,
  };
  const endExit: Point = {
    x: end.x + endDir.x * minOffset,
    y: end.y + endDir.y * minOffset,
  };

  const startH = isHorizontal(startPosition);
  const endH = isHorizontal(endPosition);

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
        // Case 2: Facing, offset — two waypoints S-shape
        // The midX must be at least startExit.x in the start's exit direction
        // and at least endExit.x in the end's exit direction.
        // When start exits right (startDir.x > 0): midX >= startExit.x
        // When end exits left (endDir.x < 0): midX <= endExit.x
        // If these constraints conflict (too close), fall back to detour path.
        const midX = (startExit.x + endExit.x) / 2;
        const startOk = startDir.x > 0 ? midX >= startExit.x : midX <= startExit.x;
        const endOk = endDir.x > 0 ? midX >= endExit.x : midX <= endExit.x;

        if (startOk && endOk) {
          return [
            { x: midX, y: start.y },
            { x: midX, y: end.y },
          ];
        }

        // Too close for S-shape — fall back to detour using exit points
        const midY = (start.y + end.y) / 2;
        return [
          startExit,
          { x: startExit.x, y: midY },
          { x: endExit.x, y: midY },
          endExit,
        ];
      }

      // Case 5: Opposing, wrong direction — detour
      // Exit both sides, route around via midY
      const midY = (start.y + end.y) / 2;
      return [
        startExit,
        { x: startExit.x, y: midY },
        { x: endExit.x, y: midY },
        endExit,
      ];
    } else {
      // Both exit vertically in opposite directions
      const facingCorrectly = startDir.y * (end.y - start.y) > 0;

      if (facingCorrectly && start.x === end.x) {
        // Case 1: Facing, aligned — zero waypoints
        return [];
      }

      if (facingCorrectly) {
        // Case 2: Facing, offset — two waypoints S-shape
        // The midY must be at least startExit.y in the start's exit direction
        // and at least endExit.y in the end's exit direction.
        // When start exits down (startDir.y > 0): midY >= startExit.y
        // When end exits up (endDir.y < 0): midY <= endExit.y
        // If these constraints conflict (too close), fall back to detour path.
        const midY = (startExit.y + endExit.y) / 2;
        const startOk = startDir.y > 0 ? midY >= startExit.y : midY <= startExit.y;
        const endOk = endDir.y > 0 ? midY >= endExit.y : midY <= endExit.y;

        if (startOk && endOk) {
          return [
            { x: start.x, y: midY },
            { x: end.x, y: midY },
          ];
        }

        // Too close for S-shape — fall back to detour using exit points
        const midX = (start.x + end.x) / 2;
        return [
          startExit,
          { x: midX, y: startExit.y },
          { x: midX, y: endExit.y },
          endExit,
        ];
      }

      // Case 5: Opposing, wrong direction — detour
      const midX = (start.x + end.x) / 2;
      return [
        startExit,
        { x: midX, y: startExit.y },
        { x: midX, y: endExit.y },
        endExit,
      ];
    }
  }

  // Case 3: Perpendicular anchors — one exits H, the other V
  if (startH !== endH) {
    if (startH) {
      // Start exits horizontally, end exits vertically
      // Natural corner at (end.x, start.y)
      const corner: Point = { x: end.x, y: start.y };
      const startOk = startDir.x * (corner.x - start.x) >= minOffset;
      const endOk = endDir.y * (corner.y - end.y) >= minOffset;

      if (startOk && endOk) {
        return [corner];
      }

      // Fallback: use exit points and route through them
      return [
        startExit,
        { x: endExit.x, y: startExit.y },
        endExit,
      ];
    } else {
      // Start exits vertically, end exits horizontally
      // Natural corner at (start.x, end.y)
      const corner: Point = { x: start.x, y: end.y };
      const startOk = startDir.y * (corner.y - start.y) >= minOffset;
      const endOk = endDir.x * (corner.x - end.x) >= minOffset;

      if (startOk && endOk) {
        return [corner];
      }

      return [
        startExit,
        { x: startExit.x, y: endExit.y },
        endExit,
      ];
    }
  }

  // Case 4: Same-side anchors — U-shape
  if (startH) {
    // Both exit horizontally in the same direction
    const outX = startDir.x > 0
      ? Math.max(startExit.x, endExit.x)
      : Math.min(startExit.x, endExit.x);
    return [
      { x: outX, y: start.y },
      { x: outX, y: end.y },
    ];
  } else {
    // Both exit vertically in the same direction
    const outY = startDir.y > 0
      ? Math.max(startExit.y, endExit.y)
      : Math.min(startExit.y, endExit.y);
    return [
      { x: start.x, y: outY },
      { x: end.x, y: outY },
    ];
  }
}
