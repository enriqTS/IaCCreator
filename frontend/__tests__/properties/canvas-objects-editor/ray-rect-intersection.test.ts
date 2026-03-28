import fc from 'fast-check';
import { describe, it, expect } from 'vitest';
import { rayRectIntersection } from '@/utils/anchor';
import type { Rect } from '@/types/diagram';

/**
 * Arbitrary for a rectangle with positive width and height.
 */
function rectArbitrary(): fc.Arbitrary<Rect> {
  return fc.record({
    x: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
    y: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
    width: fc.double({ min: 1, max: 2000, noNaN: true, noDefaultInfinity: true }),
    height: fc.double({ min: 1, max: 2000, noNaN: true, noDefaultInfinity: true }),
  });
}

/**
 * Given a rect, generate a point that is strictly outside the rect.
 * We pick a side (top/right/bottom/left) and offset beyond that edge.
 */
function externalPointArbitrary(rect: Rect): fc.Arbitrary<{ x: number; y: number }> {
  const left = rect.x;
  const right = rect.x + rect.width;
  const top = rect.y;
  const bottom = rect.y + rect.height;

  return fc.oneof(
    // Above the rect
    fc.record({
      x: fc.double({ min: left - 500, max: right + 500, noNaN: true, noDefaultInfinity: true }),
      y: fc.double({ min: top - 1000, max: top - 0.01, noNaN: true, noDefaultInfinity: true }),
    }),
    // Below the rect
    fc.record({
      x: fc.double({ min: left - 500, max: right + 500, noNaN: true, noDefaultInfinity: true }),
      y: fc.double({ min: bottom + 0.01, max: bottom + 1000, noNaN: true, noDefaultInfinity: true }),
    }),
    // Left of the rect
    fc.record({
      x: fc.double({ min: left - 1000, max: left - 0.01, noNaN: true, noDefaultInfinity: true }),
      y: fc.double({ min: top - 500, max: bottom + 500, noNaN: true, noDefaultInfinity: true }),
    }),
    // Right of the rect
    fc.record({
      x: fc.double({ min: right + 0.01, max: right + 1000, noNaN: true, noDefaultInfinity: true }),
      y: fc.double({ min: top - 500, max: bottom + 500, noNaN: true, noDefaultInfinity: true }),
    }),
  );
}

// Feature: canvas-objects-editor, Property 4: Ray-rect intersection lies on boundary
// **Validates: Requirements 2.4**
describe('Property 4: Ray-rect intersection lies on boundary', () => {
  it('intersection point lies on the rectangle boundary for any external target point', () => {
    fc.assert(
      fc.property(
        rectArbitrary().chain((rect) =>
          externalPointArbitrary(rect).map((point) => ({ rect, point }))
        ),
        ({ rect, point }) => {
          const result = rayRectIntersection(rect, point);

          const left = rect.x;
          const right = rect.x + rect.width;
          const top = rect.y;
          const bottom = rect.y + rect.height;

          const eps = 1e-6;

          // The intersection point must be within the rect bounds (with tolerance)
          expect(result.x).toBeGreaterThanOrEqual(left - eps);
          expect(result.x).toBeLessThanOrEqual(right + eps);
          expect(result.y).toBeGreaterThanOrEqual(top - eps);
          expect(result.y).toBeLessThanOrEqual(bottom + eps);

          // At least one coordinate must lie on a rect edge (within tolerance)
          const onLeftEdge = Math.abs(result.x - left) < eps;
          const onRightEdge = Math.abs(result.x - right) < eps;
          const onTopEdge = Math.abs(result.y - top) < eps;
          const onBottomEdge = Math.abs(result.y - bottom) < eps;

          expect(onLeftEdge || onRightEdge || onTopEdge || onBottomEdge).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });
});
