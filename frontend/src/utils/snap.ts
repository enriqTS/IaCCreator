import type { Point, Rect } from '@/types/diagram';

/**
 * Round a single coordinate to the nearest grid line.
 * Guards against gridSize <= 0 by returning the input unchanged.
 */
export function snapToGrid(value: number, gridSize: number): number {
  if (gridSize <= 0) return value;
  return Math.round(value / gridSize) * gridSize;
}

/**
 * Round a Point to the nearest grid intersection.
 * Guards against gridSize <= 0 by returning the input unchanged.
 */
export function snapPointToGrid(point: Point, gridSize: number): Point {
  if (gridSize <= 0) return point;
  return {
    x: snapToGrid(point.x, gridSize),
    y: snapToGrid(point.y, gridSize),
  };
}

/**
 * Round a dimension to the nearest grid multiple, enforcing a minimum.
 * @param minCells - minimum number of grid cells (default 1)
 * Guards against gridSize <= 0 by returning the input unchanged.
 */
export function snapDimension(
  value: number,
  gridSize: number,
  minCells: number = 1,
): number {
  if (gridSize <= 0) return value;
  const minValue = Math.max(1, minCells) * gridSize;
  const snapped = Math.round(value / gridSize) * gridSize;
  return Math.max(minValue, snapped);
}

/**
 * Clamp a snapped point to remain within viewport bounds (canvas coordinates).
 * Returns the point unchanged if bounds are degenerate (zero or negative dimensions).
 */
export function clampToViewport(
  point: Point,
  gridSize: number,
  viewportBounds: Rect,
): Point {
  if (viewportBounds.width <= 0 || viewportBounds.height <= 0) return point;
  if (gridSize <= 0) return point;

  const clampedX = Math.max(
    viewportBounds.x,
    Math.min(point.x, viewportBounds.x + viewportBounds.width),
  );
  const clampedY = Math.max(
    viewportBounds.y,
    Math.min(point.y, viewportBounds.y + viewportBounds.height),
  );

  return {
    x: snapToGrid(clampedX, gridSize),
    y: snapToGrid(clampedY, gridSize),
  };
}

/** Alignment guide descriptor. */
export interface AlignmentGuide {
  axis: 'horizontal' | 'vertical';
  /** Canvas coordinate of the guide line */
  position: number;
  /** Start extent of the guide line */
  from: number;
  /** End extent of the guide line */
  to: number;
  /** How much to adjust the dragged object */
  snapDelta: number;
}

/**
 * Detect alignment guides between a dragged object and all other objects.
 * Checks top, bottom, vertical-center, left, right, and horizontal-center
 * alignment within the given threshold.
 */
export function detectAlignmentGuides(
  draggedBounds: Rect,
  otherBounds: Rect[],
  threshold: number,
): AlignmentGuide[] {
  const guides: AlignmentGuide[] = [];

  const draggedLeft = draggedBounds.x;
  const draggedRight = draggedBounds.x + draggedBounds.width;
  const draggedCenterX = draggedBounds.x + draggedBounds.width / 2;
  const draggedTop = draggedBounds.y;
  const draggedBottom = draggedBounds.y + draggedBounds.height;
  const draggedCenterY = draggedBounds.y + draggedBounds.height / 2;

  for (const other of otherBounds) {
    const otherLeft = other.x;
    const otherRight = other.x + other.width;
    const otherCenterX = other.x + other.width / 2;
    const otherTop = other.y;
    const otherBottom = other.y + other.height;
    const otherCenterY = other.y + other.height / 2;

    // Horizontal extent for horizontal guide lines
    const hFrom = Math.min(draggedLeft, otherLeft);
    const hTo = Math.max(draggedRight, otherRight);

    // Vertical extent for vertical guide lines
    const vFrom = Math.min(draggedTop, otherTop);
    const vTo = Math.max(draggedBottom, otherBottom);

    // --- Horizontal guides (matching y-coordinates) ---

    // Top edge alignment
    const topDelta = otherTop - draggedTop;
    if (Math.abs(topDelta) <= threshold) {
      guides.push({
        axis: 'horizontal',
        position: otherTop,
        from: hFrom,
        to: hTo,
        snapDelta: topDelta,
      });
    }

    // Bottom edge alignment
    const bottomDelta = otherBottom - draggedBottom;
    if (Math.abs(bottomDelta) <= threshold) {
      guides.push({
        axis: 'horizontal',
        position: otherBottom,
        from: hFrom,
        to: hTo,
        snapDelta: bottomDelta,
      });
    }

    // Vertical center alignment
    const vCenterDelta = otherCenterY - draggedCenterY;
    if (Math.abs(vCenterDelta) <= threshold) {
      guides.push({
        axis: 'horizontal',
        position: otherCenterY,
        from: hFrom,
        to: hTo,
        snapDelta: vCenterDelta,
      });
    }

    // --- Vertical guides (matching x-coordinates) ---

    // Left edge alignment
    const leftDelta = otherLeft - draggedLeft;
    if (Math.abs(leftDelta) <= threshold) {
      guides.push({
        axis: 'vertical',
        position: otherLeft,
        from: vFrom,
        to: vTo,
        snapDelta: leftDelta,
      });
    }

    // Right edge alignment
    const rightDelta = otherRight - draggedRight;
    if (Math.abs(rightDelta) <= threshold) {
      guides.push({
        axis: 'vertical',
        position: otherRight,
        from: vFrom,
        to: vTo,
        snapDelta: rightDelta,
      });
    }

    // Horizontal center alignment
    const hCenterDelta = otherCenterX - draggedCenterX;
    if (Math.abs(hCenterDelta) <= threshold) {
      guides.push({
        axis: 'vertical',
        position: otherCenterX,
        from: vFrom,
        to: vTo,
        snapDelta: hCenterDelta,
      });
    }
  }

  return guides;
}

/**
 * Apply alignment snap adjustments to a position based on detected guides.
 * Uses the smallest snapDelta for each axis to avoid over-correction.
 */
export function applyAlignmentSnap(
  position: Point,
  guides: AlignmentGuide[],
): Point {
  let dx = 0;
  let dy = 0;
  let hasDx = false;
  let hasDy = false;

  for (const guide of guides) {
    if (guide.axis === 'horizontal') {
      if (!hasDy || Math.abs(guide.snapDelta) < Math.abs(dy)) {
        dy = guide.snapDelta;
        hasDy = true;
      }
    } else {
      if (!hasDx || Math.abs(guide.snapDelta) < Math.abs(dx)) {
        dx = guide.snapDelta;
        hasDx = true;
      }
    }
  }

  return {
    x: position.x + dx,
    y: position.y + dy,
  };
}

/**
 * Constrain a drag delta to the dominant axis (for Shift-drag).
 * If |dx| >= |dy|, movement is horizontal only; otherwise vertical only.
 * When both are zero, returns { dx: 0, dy: 0 }.
 */
export function constrainToAxis(
  dx: number,
  dy: number,
): { dx: number; dy: number } {
  if (dx === 0 && dy === 0) return { dx: 0, dy: 0 };
  if (Math.abs(dx) >= Math.abs(dy)) {
    return { dx, dy: 0 };
  }
  return { dx: 0, dy };
}
