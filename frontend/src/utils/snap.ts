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

/** Distribution guide — indicates equal spacing between 3+ objects. */
export interface DistributionGuide {
  axis: 'horizontal' | 'vertical';
  /** The gap (spacing) value in px that is matched. */
  gap: number;
  /** Segments to draw: each has start/end positions on the spacing axis. */
  segments: Array<{
    /** Start of the gap region (e.g., right edge of left object). */
    from: number;
    /** End of the gap region (e.g., left edge of right object). */
    to: number;
    /** Cross-axis position to center the spacing indicator. */
    crossPosition: number;
  }>;
  /** How much to adjust the dragged object to match the distribution. */
  snapDelta: number;
}

/**
 * Detect distribution (equal-spacing) guides.
 *
 * Looks for groups of 3+ objects (including the dragged one) that are evenly
 * spaced along the horizontal or vertical axis. If the dragged object can be
 * nudged to create equal spacing, returns a distribution guide with the delta.
 *
 * @param draggedBounds - Bounds of the object being dragged
 * @param otherBounds - Bounds of all other non-selected objects
 * @param threshold - Snap threshold in pixels
 * @returns Array of distribution guides (typically 0-2: one horizontal, one vertical)
 */
export function detectDistributionGuides(
  draggedBounds: Rect,
  otherBounds: Rect[],
  threshold: number,
): DistributionGuide[] {
  const guides: DistributionGuide[] = [];

  // --- Horizontal distribution (objects arranged left-to-right) ---
  const hGuide = detectAxisDistribution(draggedBounds, otherBounds, threshold, 'horizontal');
  if (hGuide) guides.push(hGuide);

  // --- Vertical distribution (objects arranged top-to-bottom) ---
  const vGuide = detectAxisDistribution(draggedBounds, otherBounds, threshold, 'vertical');
  if (vGuide) guides.push(vGuide);

  return guides;
}

/**
 * Detect distribution along a single axis.
 *
 * Strategy:
 * 1. Find objects that roughly overlap on the cross-axis (vertically for horizontal distribution)
 * 2. Sort by position along the primary axis
 * 3. Compute gaps between consecutive objects
 * 4. For each pair of objects with the dragged object between them, check if
 *    the dragged object can be placed to create equal gaps with its neighbors
 */
function detectAxisDistribution(
  draggedBounds: Rect,
  otherBounds: Rect[],
  threshold: number,
  axis: 'horizontal' | 'vertical',
): DistributionGuide | null {
  const isH = axis === 'horizontal';

  // Extract coordinates
  const dragStart = isH ? draggedBounds.x : draggedBounds.y;
  const dragEnd = isH ? draggedBounds.x + draggedBounds.width : draggedBounds.y + draggedBounds.height;
  const dragSize = isH ? draggedBounds.width : draggedBounds.height;
  const dragCross = isH
    ? draggedBounds.y + draggedBounds.height / 2
    : draggedBounds.x + draggedBounds.width / 2;

  // Filter to objects that overlap on the cross-axis (within a generous band)
  const crossOverlapThreshold = isH ? draggedBounds.height * 2 : draggedBounds.width * 2;
  const candidates = otherBounds.filter((b) => {
    const otherCross = isH ? b.y + b.height / 2 : b.x + b.width / 2;
    return Math.abs(otherCross - dragCross) < crossOverlapThreshold;
  });

  if (candidates.length < 2) return null;

  // For each pair of candidates, check if dragged can be equally spaced between them
  // Sort candidates by their start position on the primary axis
  const sorted = [...candidates].sort((a, b) => {
    const aStart = isH ? a.x : a.y;
    const bStart = isH ? b.x : b.y;
    return aStart - bStart;
  });

  // Check if placing the dragged object between consecutive pair creates equal gap
  for (let i = 0; i < sorted.length - 1; i++) {
    const leftObj = sorted[i];
    const rightObj = sorted[i + 1];

    const leftEnd = isH ? leftObj.x + leftObj.width : leftObj.y + leftObj.height;
    const rightStart = isH ? rightObj.x : rightObj.y;

    // Space between the two objects
    const totalSpace = rightStart - leftEnd;
    if (totalSpace < dragSize + 2) continue; // Not enough room for the dragged object

    // If we place dragged equally between them:
    // gap = (totalSpace - dragSize) / 2
    const equalGap = (totalSpace - dragSize) / 2;
    const idealStart = leftEnd + equalGap;
    const delta = idealStart - dragStart;

    if (Math.abs(delta) <= threshold) {
      // Found equal spacing! Build segments for visualization.
      const crossPos = isH
        ? Math.min(leftObj.y, rightObj.y, draggedBounds.y)
          + (Math.max(leftObj.y + leftObj.height, rightObj.y + rightObj.height, draggedBounds.y + draggedBounds.height)
            - Math.min(leftObj.y, rightObj.y, draggedBounds.y)) / 2
        : Math.min(leftObj.x, rightObj.x, draggedBounds.x)
          + (Math.max(leftObj.x + leftObj.width, rightObj.x + rightObj.width, draggedBounds.x + draggedBounds.width)
            - Math.min(leftObj.x, rightObj.x, draggedBounds.x)) / 2;

      const segments = [
        { from: leftEnd, to: idealStart, crossPosition: crossPos },
        { from: idealStart + dragSize, to: rightStart, crossPosition: crossPos },
      ];

      return {
        axis,
        gap: equalGap,
        segments,
        snapDelta: delta,
      };
    }
  }

  // Also check if the dragged object is at the edge and matches an existing gap
  // Check left side: is gap between dragged and its right neighbor equal to gap between the two objects after it?
  for (let i = 0; i < sorted.length - 1; i++) {
    const obj1 = sorted[i];
    const obj2 = sorted[i + 1];

    const obj1End = isH ? obj1.x + obj1.width : obj1.y + obj1.height;
    const obj2Start = isH ? obj2.x : obj2.y;
    const existingGap = obj2Start - obj1End;
    if (existingGap <= 0) continue;

    // Check if placing dragged to the left of obj1 with the same gap works
    const idealDragEnd = (isH ? obj1.x : obj1.y) - existingGap;
    const idealDragStart = idealDragEnd - dragSize;
    const deltaLeft = idealDragStart - dragStart;

    if (Math.abs(deltaLeft) <= threshold) {
      const crossPos = isH
        ? (obj1.y + obj1.height / 2 + obj2.y + obj2.height / 2) / 2
        : (obj1.x + obj1.width / 2 + obj2.x + obj2.width / 2) / 2;

      const segments = [
        { from: idealDragStart + dragSize, to: isH ? obj1.x : obj1.y, crossPosition: crossPos },
        { from: obj1End, to: obj2Start, crossPosition: crossPos },
      ];

      return {
        axis,
        gap: existingGap,
        segments,
        snapDelta: deltaLeft,
      };
    }

    // Check if placing dragged to the right of obj2 with the same gap works
    const idealDragStartRight = (isH ? obj2.x + obj2.width : obj2.y + obj2.height) + existingGap;
    const deltaRight = idealDragStartRight - dragStart;

    if (Math.abs(deltaRight) <= threshold) {
      const crossPos = isH
        ? (obj1.y + obj1.height / 2 + obj2.y + obj2.height / 2) / 2
        : (obj1.x + obj1.width / 2 + obj2.x + obj2.width / 2) / 2;

      const segments = [
        { from: obj1End, to: obj2Start, crossPosition: crossPos },
        { from: isH ? obj2.x + obj2.width : obj2.y + obj2.height, to: idealDragStartRight, crossPosition: crossPos },
      ];

      return {
        axis,
        gap: existingGap,
        segments,
        snapDelta: deltaRight,
      };
    }
  }

  return null;
}

/**
 * Apply distribution snap adjustment to a position.
 * Uses the smallest absolute snapDelta across all distribution guides.
 */
export function applyDistributionSnap(
  position: Point,
  guides: DistributionGuide[],
): Point {
  let dx = 0;
  let dy = 0;
  let hasDx = false;
  let hasDy = false;

  for (const guide of guides) {
    if (guide.axis === 'horizontal') {
      if (!hasDx || Math.abs(guide.snapDelta) < Math.abs(dx)) {
        dx = guide.snapDelta;
        hasDx = true;
      }
    } else {
      if (!hasDy || Math.abs(guide.snapDelta) < Math.abs(dy)) {
        dy = guide.snapDelta;
        hasDy = true;
      }
    }
  }

  return {
    x: position.x + dx,
    y: position.y + dy,
  };
}
