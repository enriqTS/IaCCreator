/**
 * Routing Pathfinder
 *
 * Builds an orthogonal graph from a set of spots (routing points) and
 * runs Dijkstra's algorithm with a bend penalty to find the shortest
 * path that minimizes both distance and number of turns.
 *
 * Based on the visibility-graph Dijkstra approach from draw.io/mxGraph
 * and the jose-mdz Orthogonal Connector Router.
 */

import type { Point } from '@/types/diagram';

/** Direction of travel between two connected spots. */
type Direction = 'h' | 'v' | null;

/** A node in the routing graph. */
interface GraphNode {
  point: Point;
  /** Distance from source in Dijkstra's algorithm. */
  distance: number;
  /** The path (list of nodes) from source to this node. */
  predecessorIndex: number;
  /** Direction of travel when arriving at this node. */
  arrivalDirection: Direction;
  /** Whether this node has been finalized. */
  settled: boolean;
}

/**
 * Determine the direction of a line between two points.
 * Returns 'h' for horizontal (same y), 'v' for vertical (same x), null otherwise.
 */
function getDirection(a: Point, b: Point): Direction {
  if (a.y === b.y) return 'h';
  if (a.x === b.x) return 'v';
  return null;
}

/**
 * Compute Euclidean distance between two points.
 */
function euclidean(a: Point, b: Point): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Obstacle rect for edge intersection checking.
 */
export interface ObstacleRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * Check if a horizontal line segment (same Y) intersects an obstacle rect.
 * The segment goes from (x1, y) to (x2, y) where x1 < x2.
 */
function horizontalSegmentIntersectsRect(
  x1: number,
  x2: number,
  y: number,
  rect: ObstacleRect,
): boolean {
  // Segment must overlap vertically with the rect
  if (y <= rect.top || y >= rect.top + rect.height) return false;
  // Segment must overlap horizontally with the rect
  if (x2 <= rect.left || x1 >= rect.left + rect.width) return false;
  return true;
}

/**
 * Check if a vertical line segment (same X) intersects an obstacle rect.
 * The segment goes from (x, y1) to (x, y2) where y1 < y2.
 */
function verticalSegmentIntersectsRect(
  x: number,
  y1: number,
  y2: number,
  rect: ObstacleRect,
): boolean {
  // Segment must overlap horizontally with the rect
  if (x <= rect.left || x >= rect.left + rect.width) return false;
  // Segment must overlap vertically with the rect
  if (y2 <= rect.top || y1 >= rect.top + rect.height) return false;
  return true;
}

/**
 * Build an adjacency structure from spots, respecting obstacles.
 *
 * For each spot, connects it to its nearest orthogonal neighbors:
 * - Nearest spot on the same Y with next larger X (horizontal right)
 * - Nearest spot on the same Y with next smaller X (horizontal left)
 * - Nearest spot on the same X with next larger Y (vertical down)
 * - Nearest spot on the same X with next smaller Y (vertical up)
 *
 * Edges that would pass through an obstacle are NOT created.
 *
 * Returns adjacency as a Map from spot index to array of neighbor indices.
 */
function buildAdjacency(spots: Point[], obstacles: ObstacleRect[] = []): Map<number, number[]> {
  const adjacency = new Map<number, number[]>();

  // Index spots by their X and Y coordinates for fast lookup
  const xIndex = new Map<number, Array<{ y: number; idx: number }>>();
  const yIndex = new Map<number, Array<{ x: number; idx: number }>>();

  for (let i = 0; i < spots.length; i++) {
    const p = spots[i];
    adjacency.set(i, []);

    if (!xIndex.has(p.x)) xIndex.set(p.x, []);
    xIndex.get(p.x)!.push({ y: p.y, idx: i });

    if (!yIndex.has(p.y)) yIndex.set(p.y, []);
    yIndex.get(p.y)!.push({ x: p.x, idx: i });
  }

  // Sort by coordinate for neighbor lookup
  for (const entries of xIndex.values()) {
    entries.sort((a, b) => a.y - b.y);
  }
  for (const entries of yIndex.values()) {
    entries.sort((a, b) => a.x - b.x);
  }

  // Connect adjacent spots on the same X (vertical neighbors)
  // Only connect if no obstacle lies between them
  for (const entries of xIndex.values()) {
    for (let i = 0; i < entries.length - 1; i++) {
      const a = entries[i].idx;
      const b = entries[i + 1].idx;
      const x = spots[a].x;
      const y1 = Math.min(spots[a].y, spots[b].y);
      const y2 = Math.max(spots[a].y, spots[b].y);

      let blocked = false;
      for (const obs of obstacles) {
        if (verticalSegmentIntersectsRect(x, y1, y2, obs)) {
          blocked = true;
          break;
        }
      }

      if (!blocked) {
        adjacency.get(a)!.push(b);
        adjacency.get(b)!.push(a);
      }
    }
  }

  // Connect adjacent spots on the same Y (horizontal neighbors)
  // Only connect if no obstacle lies between them
  for (const entries of yIndex.values()) {
    for (let i = 0; i < entries.length - 1; i++) {
      const a = entries[i].idx;
      const b = entries[i + 1].idx;
      const y = spots[a].y;
      const x1 = Math.min(spots[a].x, spots[b].x);
      const x2 = Math.max(spots[a].x, spots[b].x);

      let blocked = false;
      for (const obs of obstacles) {
        if (horizontalSegmentIntersectsRect(x1, x2, y, obs)) {
          blocked = true;
          break;
        }
      }

      if (!blocked) {
        adjacency.get(a)!.push(b);
        adjacency.get(b)!.push(a);
      }
    }
  }

  return adjacency;
}

/** Anchor exit direction hint for backward prevention. */
export type ExitDirection = 'up' | 'down' | 'left' | 'right';

/**
 * Run Dijkstra's algorithm with bend penalty.
 *
 * The cost to traverse an edge is: euclidean distance + bend penalty.
 * The bend penalty is applied when the direction of travel changes
 * (horizontal → vertical or vertical → horizontal). This incentivizes
 * paths with fewer turns.
 *
 * @param spots - Array of candidate routing points
 * @param sourceIndex - Index of the source spot
 * @param targetIndex - Index of the target spot
 * @param obstacles - Obstacle rects for edge intersection checking
 * @param sourceExitDir - Optional: direction the path should initially exit from source (backward prevention)
 * @param targetEntryDir - Optional: direction the path should arrive at target from (backward prevention)
 * @returns Array of points forming the shortest path, or empty array if no path found
 */
export function findShortestPath(
  spots: Point[],
  sourceIndex: number,
  targetIndex: number,
  obstacles: ObstacleRect[] = [],
  sourceExitDir?: ExitDirection,
  targetEntryDir?: ExitDirection,
): Point[] {
  if (sourceIndex === targetIndex) {
    return [spots[sourceIndex]];
  }

  const adjacency = buildAdjacency(spots, obstacles);
  const n = spots.length;

  // Dijkstra state
  const nodes: GraphNode[] = spots.map((point) => ({
    point,
    distance: Infinity,
    predecessorIndex: -1,
    arrivalDirection: null,
    settled: false,
  }));

  nodes[sourceIndex].distance = 0;

  // Simple priority queue using unsettled set
  // For better performance with large graphs, replace with a binary heap
  const unsettled = new Set<number>();
  unsettled.add(sourceIndex);

  while (unsettled.size > 0) {
    // Find the unsettled node with minimum distance
    let currentIdx = -1;
    let minDist = Infinity;
    for (const idx of unsettled) {
      if (nodes[idx].distance < minDist) {
        minDist = nodes[idx].distance;
        currentIdx = idx;
      }
    }

    if (currentIdx === -1) break;

    // Early exit if we reached the target
    if (currentIdx === targetIndex) break;

    unsettled.delete(currentIdx);
    nodes[currentIdx].settled = true;

    const current = nodes[currentIdx];
    const neighbors = adjacency.get(currentIdx);
    if (!neighbors) continue;

    for (const neighborIdx of neighbors) {
      if (nodes[neighborIdx].settled) continue;

      const neighbor = spots[neighborIdx];
      const edgeDistance = euclidean(current.point, neighbor);

      // Determine the direction of this edge
      const edgeDirection = getDirection(current.point, neighbor);

      // Backward visit prevention: penalize first hop from source going opposite to exit direction
      let backwardPenalty = 0;
      if (currentIdx === sourceIndex && sourceExitDir && edgeDirection) {
        if (isBackwardDirection(sourceExitDir, current.point, neighbor)) {
          backwardPenalty = Infinity;
        }
      }
      // Backward visit prevention: penalize arriving at target from incompatible direction
      if (neighborIdx === targetIndex && targetEntryDir && edgeDirection) {
        if (isBackwardDirection(targetEntryDir, neighbor, current.point)) {
          backwardPenalty = Infinity;
        }
      }

      // Compute bend penalty: if the direction changes, add extra cost
      let penalty = 0;
      if (current.arrivalDirection !== null && edgeDirection !== null && current.arrivalDirection !== edgeDirection) {
        // Quadratic penalty based on edge distance — strongly discourages bends
        penalty = (edgeDistance + 1) * (edgeDistance + 1);
      }

      const totalCost = current.distance + edgeDistance + penalty + backwardPenalty;

      if (totalCost < nodes[neighborIdx].distance) {
        nodes[neighborIdx].distance = totalCost;
        nodes[neighborIdx].predecessorIndex = currentIdx;
        nodes[neighborIdx].arrivalDirection = edgeDirection;
        unsettled.add(neighborIdx);
      }
    }
  }

  // Reconstruct path
  if (nodes[targetIndex].distance === Infinity) {
    return []; // No path found
  }

  const path: Point[] = [];
  let idx = targetIndex;
  while (idx !== -1) {
    path.unshift(nodes[idx].point);
    idx = nodes[idx].predecessorIndex;
  }

  return path;
}

/**
 * Simplify a path by removing collinear intermediate points.
 * Keeps only the bend points where direction changes.
 */
export function simplifyPath(points: Point[]): Point[] {
  if (points.length <= 2) return points;

  const result: Point[] = [points[0]];

  for (let i = 1; i < points.length - 1; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const next = points[i + 1];

    // Check if all three points are collinear (same x or same y)
    const sameX = prev.x === curr.x && curr.x === next.x;
    const sameY = prev.y === curr.y && curr.y === next.y;

    // Keep point only if it's a bend (not collinear)
    if (!sameX && !sameY) {
      result.push(curr);
    }
  }

  result.push(points[points.length - 1]);
  return result;
}

/**
 * Find the index of a point in the spots array.
 * Uses exact coordinate matching.
 */
export function findSpotIndex(spots: Point[], target: Point): number {
  for (let i = 0; i < spots.length; i++) {
    if (spots[i].x === target.x && spots[i].y === target.y) {
      return i;
    }
  }
  return -1;
}

/**
 * Determine if moving from `from` to `to` goes backward relative to the
 * expected exit direction. Used for backward visit prevention.
 *
 * For example, if the exit direction is 'right', moving left is backward.
 */
function isBackwardDirection(exitDir: ExitDirection, from: Point, to: Point): boolean {
  switch (exitDir) {
    case 'right': return to.x < from.x;
    case 'left': return to.x > from.x;
    case 'down': return to.y < from.y;
    case 'up': return to.y > from.y;
  }
}

/**
 * Convert an AnchorPosition to an ExitDirection for use with backward prevention.
 */
export function anchorToExitDirection(side: 'top' | 'right' | 'bottom' | 'left'): ExitDirection {
  switch (side) {
    case 'top': return 'up';
    case 'right': return 'right';
    case 'bottom': return 'down';
    case 'left': return 'left';
  }
}
