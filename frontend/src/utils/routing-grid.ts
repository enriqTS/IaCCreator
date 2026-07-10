/**
 * Routing Grid Builder
 *
 * Converts the canvas state (source, target, obstacles) into a set of
 * valid routing "spots" (candidate waypoints) by projecting rulers from
 * shape edges and generating grid intersection points that avoid obstacles.
 *
 * Based on the visibility-graph approach used by draw.io/mxGraph and the
 * jose-mdz Orthogonal Connector Router.
 */

import type { Point } from '@/types/diagram';
import type { AnchorPosition } from '@/utils/anchor';

/** A rectangle in left/top/width/height format for routing calculations. */
export interface RoutingRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/** Inflate a rect by a margin on each side. */
export function inflateRect(rect: RoutingRect, margin: number): RoutingRect {
  return {
    left: rect.left - margin,
    top: rect.top - margin,
    width: rect.width + margin * 2,
    height: rect.height + margin * 2,
  };
}

/** Check if a point is strictly inside a rect (exclusive of edges). */
function pointInsideRect(p: Point, rect: RoutingRect): boolean {
  return (
    p.x > rect.left &&
    p.x < rect.left + rect.width &&
    p.y > rect.top &&
    p.y < rect.top + rect.height
  );
}

/** Check if two rects intersect. */
export function rectsIntersect(a: RoutingRect, b: RoutingRect): boolean {
  return (
    a.left < b.left + b.width &&
    a.left + a.width > b.left &&
    a.top < b.top + b.height &&
    a.top + a.height > b.top
  );
}

/** Compute the union bounding box of multiple rects. */
function unionRects(rects: RoutingRect[]): RoutingRect {
  if (rects.length === 0) {
    return { left: 0, top: 0, width: 0, height: 0 };
  }

  let minLeft = Infinity;
  let minTop = Infinity;
  let maxRight = -Infinity;
  let maxBottom = -Infinity;

  for (const r of rects) {
    minLeft = Math.min(minLeft, r.left);
    minTop = Math.min(minTop, r.top);
    maxRight = Math.max(maxRight, r.left + r.width);
    maxBottom = Math.max(maxBottom, r.top + r.height);
  }

  return {
    left: minLeft,
    top: minTop,
    width: maxRight - minLeft,
    height: maxBottom - minTop,
  };
}

/** Extrude a point from an anchor side by a given distance. */
export function extrudePoint(point: Point, side: AnchorPosition, distance: number): Point {
  switch (side) {
    case 'top':
      return { x: point.x, y: point.y - distance };
    case 'right':
      return { x: point.x + distance, y: point.y };
    case 'bottom':
      return { x: point.x, y: point.y + distance };
    case 'left':
      return { x: point.x - distance, y: point.y };
  }
}

/** Whether an anchor side exits vertically (top/bottom). */
function isVerticalSide(side: AnchorPosition): boolean {
  return side === 'top' || side === 'bottom';
}

/** Remove duplicate values from a sorted number array. */
function uniqueSorted(arr: number[]): number[] {
  if (arr.length === 0) return arr;
  const result = [arr[0]];
  for (let i = 1; i < arr.length; i++) {
    if (arr[i] !== arr[i - 1]) {
      result.push(arr[i]);
    }
  }
  return result;
}

/**
 * Build a set of routing spots (candidate waypoints) from the given shapes.
 *
 * The algorithm:
 * 1. Inflate all rects by shapeMargin
 * 2. Project rulers from all inflated shape edges
 * 3. Add rulers for connection points
 * 4. Generate spots at ruler intersections
 * 5. Filter out spots inside obstacles
 *
 * @param sourcePoint - Connection point on the source shape
 * @param sourceSide - Which side of the source the connection exits from
 * @param sourceRect - Bounding rect of the source shape
 * @param targetPoint - Connection point on the target shape
 * @param targetSide - Which side of the target the connection enters from
 * @param targetRect - Bounding rect of the target shape
 * @param obstacles - Other shapes to avoid
 * @param shapeMargin - Padding around shapes (default 20)
 * @param globalBoundsMargin - Extra margin around the overall bounding box (default 20)
 */
export function buildRoutingSpots(
  sourcePoint: Point,
  sourceSide: AnchorPosition,
  sourceRect: RoutingRect,
  targetPoint: Point,
  targetSide: AnchorPosition,
  targetRect: RoutingRect,
  obstacles: RoutingRect[],
  shapeMargin: number = 20,
  globalBoundsMargin: number = 20,
): { spots: Point[]; sourceExit: Point; targetExit: Point; inflatedObstacles: RoutingRect[] } {
  // Inflate source and target rects
  let inflatedSource = inflateRect(sourceRect, shapeMargin);
  let inflatedTarget = inflateRect(targetRect, shapeMargin);

  // If inflated source and target overlap, reduce margin for them
  let effectiveMargin = shapeMargin;
  if (rectsIntersect(inflatedSource, inflatedTarget)) {
    effectiveMargin = 0;
    inflatedSource = sourceRect;
    inflatedTarget = targetRect;
  }

  // Inflate obstacles
  const inflatedObstacles = obstacles.map((o) => inflateRect(o, shapeMargin));

  // All inflated rects that act as blockers (source, target, and obstacles)
  const allBlockers = [inflatedSource, inflatedTarget, ...inflatedObstacles];

  // Compute exit points (extruded from the connection point by margin)
  const sourceExit = extrudePoint(sourcePoint, sourceSide, effectiveMargin);
  const targetExit = extrudePoint(targetPoint, targetSide, effectiveMargin);

  // --- Build rulers ---
  const verticals: number[] = [];
  const horizontals: number[] = [];

  // Add edges of all inflated rects as rulers
  for (const rect of allBlockers) {
    verticals.push(rect.left);
    verticals.push(rect.left + rect.width);
    horizontals.push(rect.top);
    horizontals.push(rect.top + rect.height);
  }

  // Add rulers at connection point exit coordinates
  if (isVerticalSide(sourceSide)) {
    verticals.push(sourceExit.x);
  } else {
    horizontals.push(sourceExit.y);
  }

  if (isVerticalSide(targetSide)) {
    verticals.push(targetExit.x);
  } else {
    horizontals.push(targetExit.y);
  }

  // Also add the exit point coordinates on both axes to ensure they're reachable
  verticals.push(sourceExit.x);
  horizontals.push(sourceExit.y);
  verticals.push(targetExit.x);
  horizontals.push(targetExit.y);

  // Sort and deduplicate rulers
  verticals.sort((a, b) => a - b);
  horizontals.sort((a, b) => a - b);
  const uniqueVerticals = uniqueSorted(verticals);
  const uniqueHorizontals = uniqueSorted(horizontals);

  // Compute global bounds — the bounding box of everything + margin
  const allRects = [sourceRect, targetRect, ...obstacles];
  const globalBounds = inflateRect(unionRects(allRects), shapeMargin + globalBoundsMargin);

  // --- Generate spots at all ruler intersections within bounds ---
  const spots: Point[] = [];
  const spotSet = new Set<string>(); // deduplication key

  const addSpot = (x: number, y: number) => {
    // Must be within global bounds
    if (
      x < globalBounds.left ||
      x > globalBounds.left + globalBounds.width ||
      y < globalBounds.top ||
      y > globalBounds.top + globalBounds.height
    ) {
      return;
    }

    const key = `${x},${y}`;
    if (spotSet.has(key)) return;

    // Must not be inside any blocker (inflated obstacle)
    // Exception: source/target exit points are always included
    const p: Point = { x, y };
    for (const blocker of allBlockers) {
      if (pointInsideRect(p, blocker)) {
        return;
      }
    }

    spotSet.add(key);
    spots.push(p);
  };

  // Generate spots at every grid intersection
  for (const y of uniqueHorizontals) {
    for (const x of uniqueVerticals) {
      addSpot(x, y);
    }
  }

  // Always include the exit points (even if they happen to be inside an inflated rect)
  const sourceExitKey = `${sourceExit.x},${sourceExit.y}`;
  if (!spotSet.has(sourceExitKey)) {
    spotSet.add(sourceExitKey);
    spots.push(sourceExit);
  }

  const targetExitKey = `${targetExit.x},${targetExit.y}`;
  if (!spotSet.has(targetExitKey)) {
    spotSet.add(targetExitKey);
    spots.push(targetExit);
  }

  return { spots, sourceExit, targetExit, inflatedObstacles };
}
