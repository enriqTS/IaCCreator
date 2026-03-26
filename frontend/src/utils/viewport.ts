import type { Point, Viewport } from '@/types/diagram';

/**
 * Clamp a value between a minimum and maximum.
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Convert screen (pixel) coordinates to canvas (world) coordinates.
 *
 * canvasX = (screenX - offsetX) / scale
 * canvasY = (screenY - offsetY) / scale
 */
export function screenToCanvas(screenPoint: Point, viewport: Viewport): Point {
  return {
    x: (screenPoint.x - viewport.offsetX) / viewport.scale,
    y: (screenPoint.y - viewport.offsetY) / viewport.scale,
  };
}

/**
 * Convert canvas (world) coordinates to screen (pixel) coordinates.
 *
 * screenX = canvasX * scale + offsetX
 * screenY = canvasY * scale + offsetY
 */
export function canvasToScreen(canvasPoint: Point, viewport: Viewport): Point {
  return {
    x: canvasPoint.x * viewport.scale + viewport.offsetX,
    y: canvasPoint.y * viewport.scale + viewport.offsetY,
  };
}

/**
 * Zoom the viewport at a given screen point so that the canvas point
 * under the cursor stays fixed. Scale is clamped to [0.1, 5.0].
 */
export function zoomAtPoint(viewport: Viewport, factor: number, screenCenter: Point): Viewport {
  const newScale = clamp(viewport.scale * factor, 0.1, 5.0);
  const ratio = newScale / viewport.scale;
  return {
    scale: newScale,
    offsetX: screenCenter.x - (screenCenter.x - viewport.offsetX) * ratio,
    offsetY: screenCenter.y - (screenCenter.y - viewport.offsetY) * ratio,
  };
}
