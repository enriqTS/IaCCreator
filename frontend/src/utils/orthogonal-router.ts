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
import type { RoutingRect } from '@/utils/routing-grid';
import { buildRoutingSpots, inflateRect } from '@/utils/routing-grid';
import { findShortestPath, simplifyPath, findSpotIndex } from '@/utils/routing-pathfinder';
import { computeOrthogonalWaypoints } from '@/utils/routing';
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
 * 1. Builds a visibility grid from all shapes
 * 2. Runs Dijkstra with bend penalty to find optimal path
 * 3. Simplifies the path (removes collinear points)
 * 4. Extracts waypoints (excludes start/end)
 * 5. Falls back to legacy algorithm if pathfinding fails
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

  // Build the routing grid
  const { spots, sourceExit, targetExit, inflatedObstacles } = buildRoutingSpots(
    sourcePoint,
    sourceSide,
    sourceRect,
    targetPoint,
    targetSide,
    targetRect,
    obstacles,
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
  const path = findShortestPath(spots, sourceIdx, targetIdx, allBlockers);

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
