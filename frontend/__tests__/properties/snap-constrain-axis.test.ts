/**
 * Property-based test: Shift-constrained drag locks to one axis
 *
 * Feature: canvas-snap-to-grid, Property 4: Shift-constrained drag locks to one axis
 *
 * **Validates: Requirements 2.4**
 *
 * For any starting position and any drag delta (dx, dy), when shift-constrained
 * movement is applied, exactly one of the output delta components shall be zero.
 * If |dx| >= |dy|, then the vertical component is zero; otherwise the horizontal
 * component is zero. When both dx and dy are zero, both output components are zero.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { constrainToAxis } from '@/utils/snap';

/** Arbitrary for drag deltas across a wide range. */
const deltaArb = fc.double({
  min: -10000,
  max: 10000,
  noNaN: true,
  noDefaultInfinity: true,
});

describe('Feature: canvas-snap-to-grid, Property 4: Shift-constrained drag locks to one axis', () => {
  it('constrainToAxis zeroes exactly one component based on dominant axis for non-zero deltas', () => {
    /**
     * **Validates: Requirements 2.4**
     *
     * Strategy: Generate random (dx, dy) pairs where at least one is non-zero.
     * Verify that exactly one output component is zero and the other preserves
     * the original value. The dominant axis (larger absolute value) is kept.
     */
    fc.assert(
      fc.property(deltaArb, deltaArb, (dx, dy) => {
        // Skip the (0, 0) edge case — handled separately
        fc.pre(dx !== 0 || dy !== 0);

        const result = constrainToAxis(dx, dy);

        // Exactly one component must be zero
        const dxIsZero = result.dx === 0;
        const dyIsZero = result.dy === 0;
        expect(dxIsZero !== dyIsZero).toBe(true);

        // The dominant axis is preserved, the other is zeroed
        if (Math.abs(dx) >= Math.abs(dy)) {
          // Horizontal dominant: dx preserved, dy zeroed
          expect(result.dx).toBe(dx);
          expect(result.dy).toBe(0);
        } else {
          // Vertical dominant: dy preserved, dx zeroed
          expect(result.dx).toBe(0);
          expect(result.dy).toBe(dy);
        }
      }),
      { numRuns: 100 },
    );
  });

  it('constrainToAxis returns {dx: 0, dy: 0} when both deltas are zero', () => {
    /**
     * **Validates: Requirements 2.4**
     *
     * Edge case: when both dx and dy are zero, the function returns the
     * zero vector unchanged.
     */
    const result = constrainToAxis(0, 0);
    expect(result.dx).toBe(0);
    expect(result.dy).toBe(0);
  });
});
