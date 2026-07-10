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

/**
 * Easing function: ease-in-out cubic.
 * Starts slow, accelerates, then decelerates.
 */
function easeInOutCubic(t: number): number {
  return t < 0.5
    ? 4 * t * t * t
    : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/** Active animation frame ID, used to cancel in-progress animations. */
let activeAnimationId: number | null = null;

/**
 * Animate the viewport from its current state to a target state over a given duration.
 *
 * Uses requestAnimationFrame with ease-in-out-cubic easing. If called while a
 * previous animation is running, the previous one is cancelled.
 *
 * @param getCurrentViewport - Function to get the current viewport state
 * @param setViewport - Function to set the viewport state (e.g., store setter)
 * @param target - The target viewport to animate to
 * @param duration - Animation duration in milliseconds (default: 300ms)
 */
export function animateViewport(
  getCurrentViewport: () => Viewport,
  setViewport: (viewport: Viewport) => void,
  target: Viewport,
  duration: number = 300,
): void {
  // Cancel any in-progress animation
  if (activeAnimationId !== null) {
    cancelAnimationFrame(activeAnimationId);
    activeAnimationId = null;
  }

  const start = getCurrentViewport();
  const startTime = performance.now();

  function tick(now: number) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = easeInOutCubic(progress);

    const interpolated: Viewport = {
      scale: start.scale + (target.scale - start.scale) * eased,
      offsetX: start.offsetX + (target.offsetX - start.offsetX) * eased,
      offsetY: start.offsetY + (target.offsetY - start.offsetY) * eased,
    };

    setViewport(interpolated);

    if (progress < 1) {
      activeAnimationId = requestAnimationFrame(tick);
    } else {
      activeAnimationId = null;
    }
  }

  activeAnimationId = requestAnimationFrame(tick);
}

/**
 * Cancel any in-progress viewport animation.
 * Useful when the user starts a manual pan/zoom during animation.
 */
export function cancelViewportAnimation(): void {
  if (activeAnimationId !== null) {
    cancelAnimationFrame(activeAnimationId);
    activeAnimationId = null;
  }
}
