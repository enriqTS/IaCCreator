/**
 * Routing Obstacles
 *
 * Utility to convert canvas objects into obstacle rectangles
 * for the orthogonal router.
 */

import type { CanvasObject, Rect } from '@/types/diagram';
import { getObjectBounds } from '@/types/diagram';
import type { RoutingRect } from '@/utils/routing-grid';

/**
 * Convert a Rect (x, y, width, height where x/y is top-left) to RoutingRect format.
 */
export function boundsToRoutingRect(bounds: Rect): RoutingRect {
  return {
    left: bounds.x,
    top: bounds.y,
    width: bounds.width,
    height: bounds.height,
  };
}

/**
 * Collect obstacle rects from all canvas objects, excluding specified IDs.
 *
 * @param canvasObjects - The full map of canvas objects
 * @param excludeIds - IDs to exclude (source object, target object, the line itself)
 * @returns Array of RoutingRect for obstacles the router should avoid
 */
export function collectObstacles(
  canvasObjects: Map<string, CanvasObject>,
  excludeIds: Set<string>,
): RoutingRect[] {
  const obstacles: RoutingRect[] = [];

  for (const [id, obj] of canvasObjects) {
    // Skip excluded objects (source, target, the line itself)
    if (excludeIds.has(id)) continue;

    // Lines are not obstacles — only blocks, geometric, text, uml objects
    if (obj.objectType === 'line') continue;

    const bounds = getObjectBounds(obj);
    obstacles.push(boundsToRoutingRect(bounds));
  }

  return obstacles;
}

/**
 * Create a minimal routing rect for a free-floating point (no associated shape).
 * Used when a line endpoint is not anchored to any object.
 */
export function pointToMinimalRect(point: { x: number; y: number }): RoutingRect {
  return {
    left: point.x - 1,
    top: point.y - 1,
    width: 2,
    height: 2,
  };
}
