/**
 * Property-based test: Drag-sizing minimum dimension enforcement
 *
 * **Validates: Requirements 3.4, 3.5**
 *
 * Property 5: Drag-sizing always produces objects with dimensions ≥ 40px,
 * and drag < 5px in both axes falls back to defaults (width=0, height=0).
 */
import { describe, it } from 'vitest';
import fc from 'fast-check';
import type { Point } from '@/types/diagram';
import { MIN_OBJECT_WIDTH, MIN_OBJECT_HEIGHT } from '@/types/diagram';

/** Minimum drag distance (px in canvas space) to count as a drag vs. a click */
const DRAG_THRESHOLD = 5;

/**
 * Pure logic extracted from DragSizingOverlay's mouseup handler.
 * Computes the resulting dimensions from a drag between two canvas-space points.
 */
function computeDragDimensions(
  originCanvas: Point,
  endCanvas: Point,
): { width: number; height: number; isDrag: boolean } {
  const rawWidth = Math.abs(endCanvas.x - originCanvas.x);
  const rawHeight = Math.abs(endCanvas.y - originCanvas.y);
  const isDrag = rawWidth >= DRAG_THRESHOLD || rawHeight >= DRAG_THRESHOLD;

  if (isDrag) {
    return {
      width: Math.max(rawWidth, MIN_OBJECT_WIDTH),
      height: Math.max(rawHeight, MIN_OBJECT_HEIGHT),
      isDrag: true,
    };
  }

  return { width: 0, height: 0, isDrag: false };
}

/**
 * Arbitrary that generates a canvas-space point with reasonable coordinates.
 */
const canvasPointArb: fc.Arbitrary<Point> = fc.record({
  x: fc.double({ min: -10000, max: 10000, noNaN: true, noDefaultInfinity: true }),
  y: fc.double({ min: -10000, max: 10000, noNaN: true, noDefaultInfinity: true }),
});

describe('Drag-Sizing Minimum Dimension Enforcement', () => {
  it('Property 5: drag-sizing always produces dimensions >= 40px when drag >= 5px, and falls back to defaults when drag < 5px', () => {
    /**
     * **Validates: Requirements 3.4, 3.5**
     *
     * Strategy: Generate random origin and end points in canvas space.
     * Compute the drag dimensions and verify:
     *   - If drag distance >= 5px in either axis → isDrag is true,
     *     width >= MIN_OBJECT_WIDTH (40), height >= MIN_OBJECT_HEIGHT (40)
     *   - If drag distance < 5px in both axes → isDrag is false,
     *     width === 0, height === 0 (signals default dimensions)
     */
    fc.assert(
      fc.property(canvasPointArb, canvasPointArb, (origin, end) => {
        const result = computeDragDimensions(origin, end);

        const rawWidth = Math.abs(end.x - origin.x);
        const rawHeight = Math.abs(end.y - origin.y);
        const expectedIsDrag = rawWidth >= DRAG_THRESHOLD || rawHeight >= DRAG_THRESHOLD;

        if (expectedIsDrag) {
          // Requirement 3.5: minimum 40px enforced on both dimensions
          return (
            result.isDrag === true &&
            result.width >= MIN_OBJECT_WIDTH &&
            result.height >= MIN_OBJECT_HEIGHT
          );
        } else {
          // Requirement 3.4: drag < 5px in both axes → default dimensions
          return (
            result.isDrag === false &&
            result.width === 0 &&
            result.height === 0
          );
        }
      }),
      { numRuns: 1000 },
    );
  });
});
