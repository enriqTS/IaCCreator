/**
 * Orthogonal Router — Entry Point
 *
 * Orchestrates the grid builder and pathfinder to produce an obstacle-aware
 * orthogonal route between two connection points. Falls back to the legacy
 * `computeOrthogonalWaypoints` when pathfinding fails.
 *
 * This is the primary function that replaces `computeOrthogonalWaypoints`
 * in all rendering components.
 */

import type { Point } from '@/types/diagram';
import type { AnchorPosition } from '@/utils/anchor';
import type { RoutingRect } from './routing-grid';
import { buildRoutingSpots, inflateRect } from './routing-grid';
import { findShortestPath, simplifyPath, findSpotIndex, anchorToExitDirection } from './routing-pathfinder';
import { computeOrthogonalWaypoints } from './routing';
import { snapToGrid } from '@/utils/snap';

/** Input for the orthogonal router. */
export interface RoutingRequest {
  /** Connection point on the source shape (anchor point). */
  sourcePoint: Point;
  /** Which side of the source the connection exits from. */
  sourceSide: AnchorPosition;
  /** Bounding rect of the source shape. */
  sourceRect: RoutingRect;
  /** Connection point on the target shape (anchor point). */
  targetPoint: Point;
  /** Which side of the target the connection enters from. */
  targetSide: AnchorPosition;
  /** Bounding rect of the target shape. */
  targetRect: RoutingRect;
  /** Other shapes to route around. */
  obstacles: RoutingRect[];
  /** Padding around shapes for route clearance (default: 20). */
  shapeMargin?: number;
  /** Grid size for snapping waypoints (optional). */
  gridSize?: number;
}

/** Output from the orthogonal router. */
export interface RoutingResult {
  /** Intermediate waypoints (excludes sourcePoint and targetPoint). */
  waypoints: Point[];
  /** Whether the pathfinder found a valid route (false = used fallback). */
  success: boolean;
}

/**
 * Route an orthogonal connector between two points, avoiding obstacles.
 *
 * This function:
 * 1. Handles special cases (same point, self-connection)
 * 2. Filters obstacles for performance on large diagrams
 * 3. Builds a visibility grid from all shapes
 * 4. Runs Dijkstra with bend penalty to find optimal path
 * 5. Simplifies the path (removes collinear points)
 * 6. Extracts waypoints (excludes start/end)
 * 7. Falls back to legacy algorithm if pathfinding fails
 */
export function routeOrthogonalConnector(request: RoutingRequest): RoutingResult {
  const {
    sourcePoint,
    sourceSide,
    sourceRect,
    targetPoint,
    targetSide,
    targetRect,
    obstacles,
    shapeMargin = 20,
    gridSize,
  } = request;

  // Degenerate case: source and target are the same point
  if (sourcePoint.x === targetPoint.x && sourcePoint.y === targetPoint.y) {
    return { waypoints: [], success: true };
  }

  // Self-connection: source and target are on the same object (rects are identical)
  if (
    sourceRect.left === targetRect.left &&
    sourceRect.top === targetRect.top &&
    sourceRect.width === targetRect.width &&
    sourceRect.height === targetRect.height
  ) {
    return selfConnectionRoute(sourcePoint, sourceSide, targetPoint, targetSide, sourceRect, shapeMargin, gridSize);
  }

  // Short-distance optimization: skip full router for very close shapes
  const shortResult = shortDistanceRoute(
    sourcePoint, sourceSide, targetPoint, targetSide,
    sourceRect, targetRect, shapeMargin,
  );
  if (shortResult) {
    // Apply grid snap if requested
    if (gridSize && gridSize > 0) {
      shortResult.waypoints = shortResult.waypoints.map((p) => ({
        x: snapToGrid(p.x, gridSize),
        y: snapToGrid(p.y, gridSize),
      }));
    }
    return shortResult;
  }

  // Large-diagram optimization: limit obstacles to those within proximity
  // of the source-target bounding box to keep pathfinding fast.
  const filteredObstacles = filterObstaclesByProximity(
    obstacles,
    sourceRect,
    targetRect,
    shapeMargin,
  );

  // Build the routing grid
  const { spots, sourceExit, targetExit, inflatedObstacles } = buildRoutingSpots(
    sourcePoint,
    sourceSide,
    sourceRect,
    targetPoint,
    targetSide,
    targetRect,
    filteredObstacles,
    shapeMargin,
  );

  // Find source and target indices in the spots array
  const sourceIdx = findSpotIndex(spots, sourceExit);
  const targetIdx = findSpotIndex(spots, targetExit);

  // If exit points aren't in the grid, fall back
  if (sourceIdx === -1 || targetIdx === -1) {
    return fallback(sourcePoint, sourceSide, targetPoint, targetSide, gridSize);
  }

  // Run pathfinding with obstacle-aware edge checking
  // Pass all blockers (inflated obstacles + source/target rects) for edge intersection
  const inflatedSource = inflateRect(sourceRect, shapeMargin);
  const inflatedTarget = inflateRect(targetRect, shapeMargin);
  const allBlockers = [inflatedSource, inflatedTarget, ...inflatedObstacles];

  // Backward visit prevention: constrain first/last hops to compatible directions
  const sourceExitDir = anchorToExitDirection(sourceSide);
  const targetEntryDir = anchorToExitDirection(targetSide);
  const path = findShortestPath(spots, sourceIdx, targetIdx, allBlockers, sourceExitDir, targetEntryDir);

  // If no path found, fall back
  if (path.length === 0) {
    return fallback(sourcePoint, sourceSide, targetPoint, targetSide, gridSize);
  }

  // Build full path: sourcePoint → [exit path] → targetPoint
  const fullPath = [sourcePoint, ...path, targetPoint];

  // Simplify: remove collinear intermediate points
  const simplified = simplifyPath(fullPath);

  // Extract waypoints: everything between sourcePoint and targetPoint
  // simplified[0] === sourcePoint, simplified[last] === targetPoint
  let waypoints = simplified.slice(1, simplified.length - 1);

  // Balance S-shaped routes: center the shared segment between shapes
  waypoints = balancePath(waypoints, sourcePoint, targetPoint, sourceRect, targetRect);

  // Apply grid snap if requested
  if (gridSize && gridSize > 0) {
    waypoints = waypoints.map((p) => ({
      x: snapToGrid(p.x, gridSize),
      y: snapToGrid(p.y, gridSize),
    }));
  }

  return { waypoints, success: true };
}

/**
 * Balance S-shaped routes by centering the shared (middle) segment.
 *
 * An S-shaped route has exactly 2 waypoints forming 2 turns. The middle
 * segment connects the two waypoints. This function repositions that
 * segment to be centered between the source and target shapes' relevant edges.
 *
 * For more complex routes (>2 waypoints), no balancing is applied.
 */
export function balancePath(
  waypoints: Point[],
  sourcePoint: Point,
  targetPoint: Point,
  sourceRect: RoutingRect,
  targetRect: RoutingRect,
): Point[] {
  // Only balance S-shaped routes (exactly 2 waypoints = 2 turns)
  if (waypoints.length !== 2) return waypoints;

  const [wp1, wp2] = waypoints;

  // Determine if the middle segment is horizontal or vertical
  if (wp1.x === wp2.x) {
    // Middle segment is vertical (shared X). Balance the X coordinate.
    // The range is between the nearest edges of source and target on the X axis.
    const sourceRight = sourceRect.left + sourceRect.width;
    const targetRight = targetRect.left + targetRect.width;

    let minX: number;
    let maxX: number;

    if (sourcePoint.x <= targetPoint.x) {
      // Source is to the left, target is to the right
      minX = sourceRight;
      maxX = targetRect.left;
    } else {
      // Source is to the right, target is to the left
      minX = targetRight;
      maxX = sourceRect.left;
    }

    // Only balance if there's actual space between the shapes
    if (minX < maxX) {
      const centeredX = Math.round((minX + maxX) / 2);
      return [
        { x: centeredX, y: wp1.y },
        { x: centeredX, y: wp2.y },
      ];
    }
  } else if (wp1.y === wp2.y) {
    // Middle segment is horizontal (shared Y). Balance the Y coordinate.
    const sourceBottom = sourceRect.top + sourceRect.height;
    const targetBottom = targetRect.top + targetRect.height;

    let minY: number;
    let maxY: number;

    if (sourcePoint.y <= targetPoint.y) {
      // Source is above, target is below
      minY = sourceBottom;
      maxY = targetRect.top;
    } else {
      // Source is below, target is above
      minY = targetBottom;
      maxY = sourceRect.top;
    }

    // Only balance if there's actual space between the shapes
    if (minY < maxY) {
      const centeredY = Math.round((minY + maxY) / 2);
      return [
        { x: wp1.x, y: centeredY },
        { x: wp2.x, y: centeredY },
      ];
    }
  }

  return waypoints;
}

/**
 * Handle short-distance routing without invoking the full grid router.
 *
 * When shapes are very close (Manhattan distance between connection points < 2 * shapeMargin)
 * and don't overlap, use simple geometric rules:
 * - Facing anchors: 0 waypoints (straight line)
 * - Perpendicular anchors: 1 waypoint (single corner)
 * - Same-side anchors: minimal U-shape with reduced offset
 *
 * Returns null if not applicable (shapes too far apart or overlapping).
 */
export function shortDistanceRoute(
  sourcePoint: Point,
  sourceSide: AnchorPosition,
  targetPoint: Point,
  targetSide: AnchorPosition,
  sourceRect: RoutingRect,
  targetRect: RoutingRect,
  shapeMargin: number,
): RoutingResult | null {
  const manhattan = Math.abs(targetPoint.x - sourcePoint.x) + Math.abs(targetPoint.y - sourcePoint.y);

  // Only apply for very close shapes
  if (manhattan >= 2 * shapeMargin) return null;

  // Don't apply if shapes overlap (let the full router handle it)
  if (rectsOverlap(sourceRect, targetRect)) return null;

  if (areOppositeSides(sourceSide, targetSide)) {
    // Facing anchors: can potentially connect directly
    if (isFacingDirect(sourcePoint, sourceSide, targetPoint)) {
      return { waypoints: [], success: true };
    }
    // Not directly facing — use a single-segment S with minimal offset
    const midOffset = Math.max(shapeMargin / 2, 4);
    if (isVerticalAnchor(sourceSide)) {
      const midY = Math.round((sourcePoint.y + targetPoint.y) / 2);
      return {
        waypoints: [
          { x: sourcePoint.x, y: midY },
          { x: targetPoint.x, y: midY },
        ],
        success: true,
      };
    } else {
      const midX = Math.round((sourcePoint.x + targetPoint.x) / 2);
      return {
        waypoints: [
          { x: midX, y: sourcePoint.y },
          { x: midX, y: targetPoint.y },
        ],
        success: true,
      };
    }
  }

  if (sourceSide === targetSide) {
    // Same-side anchors: minimal U-shape
    const offset = Math.max(shapeMargin / 2, 8);
    const exitPt = extrudeFromSide(sourcePoint, sourceSide, offset);
    const entryPt = extrudeFromSide(targetPoint, targetSide, offset);
    return { waypoints: [exitPt, entryPt], success: true };
  }

  // Perpendicular anchors: single corner
  const corner = computePerpendicularCorner(sourcePoint, sourceSide, targetPoint, targetSide);
  if (corner) {
    return { waypoints: [corner], success: true };
  }

  return null;
}

/** Check if a source point directly faces the target point (correct direction). */
function isFacingDirect(sourcePoint: Point, sourceSide: AnchorPosition, targetPoint: Point): boolean {
  switch (sourceSide) {
    case 'right': return targetPoint.x >= sourcePoint.x && targetPoint.y === sourcePoint.y;
    case 'left': return targetPoint.x <= sourcePoint.x && targetPoint.y === sourcePoint.y;
    case 'bottom': return targetPoint.y >= sourcePoint.y && targetPoint.x === sourcePoint.x;
    case 'top': return targetPoint.y <= sourcePoint.y && targetPoint.x === sourcePoint.x;
  }
}

/** Compute a single corner point for perpendicular anchor connections. */
function computePerpendicularCorner(
  sourcePoint: Point,
  sourceSide: AnchorPosition,
  targetPoint: Point,
  targetSide: AnchorPosition,
): Point | null {
  // Source exits horizontally, target exits vertically → corner at (sourceExit.x-direction, targetEntry.y-direction)
  if (!isVerticalAnchor(sourceSide) && isVerticalAnchor(targetSide)) {
    return { x: targetPoint.x, y: sourcePoint.y };
  }
  // Source exits vertically, target exits horizontally → corner at (source.x, target.y)
  if (isVerticalAnchor(sourceSide) && !isVerticalAnchor(targetSide)) {
    return { x: sourcePoint.x, y: targetPoint.y };
  }
  return null;
}

/** Check if two rects overlap (any intersection). */
function rectsOverlap(a: RoutingRect, b: RoutingRect): boolean {
  return (
    a.left < b.left + b.width &&
    a.left + a.width > b.left &&
    a.top < b.top + b.height &&
    a.top + a.height > b.top
  );
}

/**
 * Fallback to the legacy routing algorithm.
 * Used when the grid-based pathfinder cannot find a valid route.
 */
function fallback(
  sourcePoint: Point,
  sourceSide: AnchorPosition,
  targetPoint: Point,
  targetSide: AnchorPosition,
  gridSize?: number,
): RoutingResult {
  const waypoints = computeOrthogonalWaypoints(
    sourcePoint,
    sourceSide,
    targetPoint,
    targetSide,
    undefined,
    gridSize,
  );
  return { waypoints, success: false };
}

/**
 * Generate a U-shaped detour route for self-connections (same source and target object).
 *
 * The route exits from the source side, travels outward by shapeMargin,
 * wraps around the shape, and enters from the target side.
 */
function selfConnectionRoute(
  sourcePoint: Point,
  sourceSide: AnchorPosition,
  targetPoint: Point,
  targetSide: AnchorPosition,
  rect: RoutingRect,
  shapeMargin: number,
  gridSize?: number,
): RoutingResult {
  const offset = shapeMargin * 1.5;

  // Compute the exit and entry points extruded from the shape
  const exitPt = extrudeFromSide(sourcePoint, sourceSide, offset);
  const entryPt = extrudeFromSide(targetPoint, targetSide, offset);

  let waypoints: Point[];

  if (sourceSide === targetSide) {
    // Same side: simple U-shape — exit, move laterally to align, enter
    // The two extruded points share the same outward coordinate, just connect them
    waypoints = [exitPt, entryPt];
  } else if (areOppositeSides(sourceSide, targetSide)) {
    // Opposite sides: route around one side of the shape
    // Choose to go around the shorter dimension
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;

    if (isVerticalAnchor(sourceSide)) {
      // Source exits top/bottom, target exits bottom/top → go around left or right
      const goRight = sourcePoint.x >= cx;
      const cornerX = goRight ? rect.left + rect.width + offset : rect.left - offset;
      waypoints = [
        exitPt,
        { x: cornerX, y: exitPt.y },
        { x: cornerX, y: entryPt.y },
        entryPt,
      ];
    } else {
      // Source exits left/right, target exits right/left → go around top or bottom
      const goDown = sourcePoint.y >= cy;
      const cornerY = goDown ? rect.top + rect.height + offset : rect.top - offset;
      waypoints = [
        exitPt,
        { x: exitPt.x, y: cornerY },
        { x: entryPt.x, y: cornerY },
        entryPt,
      ];
    }
  } else {
    // Perpendicular sides: L-shaped with one corner at the intersection of exit directions
    const corner: Point = { x: exitPt.x, y: exitPt.y };

    if (isVerticalAnchor(sourceSide)) {
      // Source exits vertically → corner shares exitPt.y with source exit, entryPt.x with target exit... 
      // Actually: exit goes vertically out, entry goes horizontally out. Corner at (entryPt.x, exitPt.y)
      corner.x = entryPt.x;
      corner.y = exitPt.y;
    } else {
      // Source exits horizontally → corner at (exitPt.x, entryPt.y)
      corner.x = exitPt.x;
      corner.y = entryPt.y;
    }

    waypoints = [exitPt, corner, entryPt];
  }

  // Apply grid snap if requested
  if (gridSize && gridSize > 0) {
    waypoints = waypoints.map((p) => ({
      x: snapToGrid(p.x, gridSize),
      y: snapToGrid(p.y, gridSize),
    }));
  }

  return { waypoints, success: true };
}

/** Extrude a point outward from a side by a given distance. */
function extrudeFromSide(point: Point, side: AnchorPosition, distance: number): Point {
  switch (side) {
    case 'top': return { x: point.x, y: point.y - distance };
    case 'bottom': return { x: point.x, y: point.y + distance };
    case 'left': return { x: point.x - distance, y: point.y };
    case 'right': return { x: point.x + distance, y: point.y };
  }
}

/** Check if two sides are opposite (top/bottom or left/right). */
function areOppositeSides(a: AnchorPosition, b: AnchorPosition): boolean {
  return (
    (a === 'top' && b === 'bottom') ||
    (a === 'bottom' && b === 'top') ||
    (a === 'left' && b === 'right') ||
    (a === 'right' && b === 'left')
  );
}

/** Check if an anchor side exits vertically (top or bottom). */
function isVerticalAnchor(side: AnchorPosition): boolean {
  return side === 'top' || side === 'bottom';
}

/** Maximum number of obstacles before spatial filtering kicks in. */
const OBSTACLE_PROXIMITY_THRESHOLD = 50;

/**
 * Filter obstacles to only include those within a reasonable proximity
 * of the source-target bounding box. This prevents performance degradation
 * on large diagrams (50+ shapes).
 *
 * Strategy: compute the bounding box enclosing source and target, inflate it
 * by 2× the source-target distance, and discard obstacles fully outside.
 */
export function filterObstaclesByProximity(
  obstacles: RoutingRect[],
  sourceRect: RoutingRect,
  targetRect: RoutingRect,
  shapeMargin: number,
): RoutingRect[] {
  // If few obstacles, skip filtering entirely
  if (obstacles.length <= OBSTACLE_PROXIMITY_THRESHOLD) {
    return obstacles;
  }

  // Compute bounding box of source + target
  const minLeft = Math.min(sourceRect.left, targetRect.left);
  const minTop = Math.min(sourceRect.top, targetRect.top);
  const maxRight = Math.max(
    sourceRect.left + sourceRect.width,
    targetRect.left + targetRect.width,
  );
  const maxBottom = Math.max(
    sourceRect.top + sourceRect.height,
    targetRect.top + targetRect.height,
  );

  // Compute the diagonal distance between source and target centers
  const scx = sourceRect.left + sourceRect.width / 2;
  const scy = sourceRect.top + sourceRect.height / 2;
  const tcx = targetRect.left + targetRect.width / 2;
  const tcy = targetRect.top + targetRect.height / 2;
  const dist = Math.sqrt((tcx - scx) ** 2 + (tcy - scy) ** 2);

  // Inflate by max(2× distance, shapeMargin * 4) to capture relevant obstacles
  const inflation = Math.max(dist, shapeMargin * 4);
  const filterLeft = minLeft - inflation;
  const filterTop = minTop - inflation;
  const filterRight = maxRight + inflation;
  const filterBottom = maxBottom + inflation;

  return obstacles.filter((obs) => {
    const obsRight = obs.left + obs.width;
    const obsBottom = obs.top + obs.height;

    // Keep if the obstacle overlaps the filter region
    return (
      obsRight >= filterLeft &&
      obs.left <= filterRight &&
      obsBottom >= filterTop &&
      obs.top <= filterBottom
    );
  });
}
