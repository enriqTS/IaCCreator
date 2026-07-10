import type { Point, Rect } from '@/types/diagram';

/** Cardinal anchor positions on a bounding rect */
export type AnchorPosition = 'top' | 'right' | 'bottom' | 'left';

/** Snap threshold in canvas pixels */
export const SNAP_THRESHOLD = 20;

/** Get the 4 cardinal anchor points for an object's bounding rect */
export function getAnchorPoints(bounds: Rect): Record<AnchorPosition, Point> {
  const cx = bounds.x + bounds.width / 2;
  const cy = bounds.y + bounds.height / 2;
  return {
    top: { x: cx, y: bounds.y },
    right: { x: bounds.x + bounds.width, y: cy },
    bottom: { x: cx, y: bounds.y + bounds.height },
    left: { x: bounds.x, y: cy },
  };
}

/**
 * Compute the anchor point on a rect's edge closest to a given external point.
 * Projects the external point onto each edge and returns the nearest one.
 */
export function computeAnchorPoint(bounds: Rect, externalPoint: Point): Point {
  const left = bounds.x;
  const right = bounds.x + bounds.width;
  const top = bounds.y;
  const bottom = bounds.y + bounds.height;

  // Clamp helper
  const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v));

  // Candidate points: closest point on each edge
  const candidates: Point[] = [
    // Top edge
    { x: clamp(externalPoint.x, left, right), y: top },
    // Right edge
    { x: right, y: clamp(externalPoint.y, top, bottom) },
    // Bottom edge
    { x: clamp(externalPoint.x, left, right), y: bottom },
    // Left edge
    { x: left, y: clamp(externalPoint.y, top, bottom) },
  ];

  let best = candidates[0];
  let bestDist = Infinity;
  for (const c of candidates) {
    const dx = c.x - externalPoint.x;
    const dy = c.y - externalPoint.y;
    const dist = dx * dx + dy * dy;
    if (dist < bestDist) {
      bestDist = dist;
      best = c;
    }
  }
  return best;
}

/**
 * Ray-rect intersection: given a rect center and a target point,
 * find where the ray from center→target intersects the rect boundary.
 * If the target is at the center, returns the center point.
 */
export function rayRectIntersection(rect: Rect, target: Point): Point {
  const cx = rect.x + rect.width / 2;
  const cy = rect.y + rect.height / 2;

  const dx = target.x - cx;
  const dy = target.y - cy;

  // Target is at center — no meaningful direction
  if (dx === 0 && dy === 0) {
    return { x: cx, y: cy };
  }

  const halfW = rect.width / 2;
  const halfH = rect.height / 2;

  // Compute t for intersection with each edge
  // Ray: P = center + t * (target - center), t > 0
  let t = Infinity;

  if (dx !== 0) {
    // Right edge (x = cx + halfW) when dx > 0, left edge (x = cx - halfW) when dx < 0
    const tx = (dx > 0 ? halfW : -halfW) / dx;
    const yAtTx = cy + tx * dy;
    if (tx > 0 && yAtTx >= rect.y - 1e-9 && yAtTx <= rect.y + rect.height + 1e-9) {
      t = Math.min(t, tx);
    }
  }

  if (dy !== 0) {
    // Bottom edge (y = cy + halfH) when dy > 0, top edge (y = cy - halfH) when dy < 0
    const ty = (dy > 0 ? halfH : -halfH) / dy;
    const xAtTy = cx + ty * dx;
    if (ty > 0 && xAtTy >= rect.x - 1e-9 && xAtTy <= rect.x + rect.width + 1e-9) {
      t = Math.min(t, ty);
    }
  }

  if (!isFinite(t)) {
    return { x: cx, y: cy };
  }

  return {
    x: cx + t * dx,
    y: cy + t * dy,
  };
}

/**
 * Check if a point is within snap threshold of any anchor on a rect.
 * Returns the closest anchor point if within threshold, or null otherwise.
 */
export function findSnapAnchor(
  point: Point,
  bounds: Rect,
  threshold: number = SNAP_THRESHOLD,
): Point | null {
  const anchors = getAnchorPoints(bounds);
  const anchorList = Object.values(anchors) as Point[];

  let best: Point | null = null;
  let bestDist = threshold * threshold; // compare squared distances

  for (const anchor of anchorList) {
    const dx = anchor.x - point.x;
    const dy = anchor.y - point.y;
    const distSq = dx * dx + dy * dy;
    if (distSq <= bestDist) {
      bestDist = distSq;
      best = anchor;
    }
  }

  return best;
}

/**
 * Find the cardinal anchor position on a bounding rect closest to a given point.
 * Uses Euclidean distance to each of the four anchor points.
 * When `currentPosition` is provided and ties with another anchor, retains `currentPosition`.
 */
export function findNearestAnchorPosition(
  point: Point,
  bounds: Rect,
  currentPosition?: AnchorPosition,
): AnchorPosition {
  const anchors = getAnchorPoints(bounds);
  const positions: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

  let bestPosition: AnchorPosition = positions[0];
  let bestDist = Infinity;

  for (const pos of positions) {
    const anchor = anchors[pos];
    const dx = anchor.x - point.x;
    const dy = anchor.y - point.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    if (dist < bestDist) {
      bestDist = dist;
      bestPosition = pos;
    } else if (dist === bestDist && pos === currentPosition) {
      // Tie: retain currentPosition to avoid flickering
      bestPosition = pos;
    }
  }

  return bestPosition;
}

/**
 * Compute the optimal exit side from a source shape toward a target center point,
 * using a heading-based approach. This produces more intuitive anchor selections
 * than nearest-distance when shapes are at angles.
 *
 * Determines which cardinal direction (top/right/bottom/left) the target center
 * lies in relative to the source center, favoring the dominant axis.
 *
 * @param sourceBounds - Bounding rect of the source shape
 * @param targetCenter - Center point of the target shape
 * @param currentPosition - If provided and the result is ambiguous (45° angle), retain this
 */
export function computeOptimalExitSide(
  sourceBounds: Rect,
  targetCenter: Point,
  currentPosition?: AnchorPosition,
): AnchorPosition {
  const cx = sourceBounds.x + sourceBounds.width / 2;
  const cy = sourceBounds.y + sourceBounds.height / 2;
  const dx = targetCenter.x - cx;
  const dy = targetCenter.y - cy;

  // Exact tie (same center): retain current or default to 'right'
  if (dx === 0 && dy === 0) {
    return currentPosition ?? 'right';
  }

  // At exactly 45°, retain current position to avoid flickering
  if (Math.abs(dx) === Math.abs(dy) && currentPosition) {
    return currentPosition;
  }

  if (Math.abs(dx) >= Math.abs(dy)) {
    return dx >= 0 ? 'right' : 'left';
  }
  return dy >= 0 ? 'bottom' : 'top';
}

/**
 * Check if a point is within snap threshold of any anchor on a rect.
 * Returns the closest anchor point and its position if within threshold, or null otherwise.
 */
export function findSnapAnchorWithPosition(
  point: Point,
  bounds: Rect,
  threshold: number = SNAP_THRESHOLD,
): { point: Point; position: AnchorPosition } | null {
  const anchors = getAnchorPoints(bounds);
  const positions = Object.keys(anchors) as AnchorPosition[];

  let best: { point: Point; position: AnchorPosition } | null = null;
  let bestDist = threshold * threshold; // compare squared distances

  for (const pos of positions) {
    const anchor = anchors[pos];
    const dx = anchor.x - point.x;
    const dy = anchor.y - point.y;
    const distSq = dx * dx + dy * dy;
    if (distSq <= bestDist) {
      bestDist = distSq;
      best = { point: anchor, position: pos };
    }
  }

  return best;
}
