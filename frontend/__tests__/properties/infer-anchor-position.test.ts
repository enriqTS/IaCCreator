/**
 * Property-based test: Inferred anchor position consistency
 *
 * Feature: line-segment-manipulation, Property 3: Inferred anchor position consistency
 *
 * **Validates: Requirements 2.3**
 *
 * For any two distinct points (from, to), `inferAnchorPosition(from, to)` returns
 * consistent with the dominant direction: if |dx| >= |dy|, result is 'right' (dx > 0)
 * or 'left' (dx < 0); otherwise 'bottom' (dy > 0) or 'top' (dy < 0).
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { inferAnchorPosition } from '@/utils/routing';
import type { Point } from '@/types/diagram';

/** Arbitrary for coordinate values across a wide range. */
const coordArb = fc.integer({ min: -5000, max: 5000 });

/** Arbitrary for a Point. */
const pointArb: fc.Arbitrary<Point> = fc.record({ x: coordArb, y: coordArb });

/**
 * Arbitrary for two distinct points (from, to) where at least one of dx or dy is non-zero.
 * This filters out the degenerate case where from === to.
 */
const distinctPointPairArb = fc
  .tuple(pointArb, pointArb)
  .filter(([from, to]) => from.x !== to.x || from.y !== to.y);

describe('Feature: line-segment-manipulation, Property 3: Inferred anchor position consistency', () => {
  it('returns direction consistent with dominant axis for any two distinct points', () => {
    /**
     * **Validates: Requirements 2.3**
     *
     * Strategy: Generate pairs of distinct points. Compute dx and dy.
     * If |dx| >= |dy|, expect 'right' or 'left' based on sign of dx.
     * If |dy| > |dx|, expect 'bottom' or 'top' based on sign of dy.
     */
    fc.assert(
      fc.property(distinctPointPairArb, ([from, to]) => {
        const result = inferAnchorPosition(from, to);

        const dx = to.x - from.x;
        const dy = to.y - from.y;

        if (Math.abs(dx) >= Math.abs(dy)) {
          // Horizontal dominant (or equal)
          const expected = dx > 0 ? 'right' : 'left';
          expect(result).toBe(expected);
        } else {
          // Vertical dominant
          const expected = dy > 0 ? 'bottom' : 'top';
          expect(result).toBe(expected);
        }
      }),
      { numRuns: 100 },
    );
  });

  it('returns "right" as default when from and to are the same point', () => {
    /**
     * **Validates: Requirements 2.3**
     *
     * Edge case: coincident points should return the default 'right'.
     */
    fc.assert(
      fc.property(pointArb, (point) => {
        const result = inferAnchorPosition(point, point);
        expect(result).toBe('right');
      }),
      { numRuns: 100 },
    );
  });
});
