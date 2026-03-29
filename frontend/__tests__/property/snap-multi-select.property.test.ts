/**
 * Property-based test: Multi-select snap preserves relative positions
 *
 * Feature: canvas-snap-to-grid, Property 3: Multi-select snap preserves relative positions
 *
 * **Validates: Requirements 2.2**
 *
 * For any set of canvas objects with arbitrary positions, when the primary object
 * is snapped to the grid and all others are moved by the same delta, the relative
 * displacement between any two objects in the set shall be identical before and
 * after the snap-drag operation.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { snapToGrid } from '@/utils/snap';
import type { Point } from '@/types/diagram';

/** Arbitrary for valid grid cell sizes per the spec: integers in [5, 100]. */
const gridSizeArb = fc.integer({ min: 5, max: 100 });

/** Arbitrary for a coordinate value across a wide range. */
const coordinateArb = fc.double({
  min: -10000,
  max: 10000,
  noNaN: true,
  noDefaultInfinity: true,
});

/** Arbitrary for a canvas Point with reasonable coordinates. */
const pointArb: fc.Arbitrary<Point> = fc.record({
  x: coordinateArb,
  y: coordinateArb,
});

/**
 * Arbitrary for a non-empty array of 2–10 object positions.
 * The first element is treated as the "primary" object.
 */
const positionSetArb = fc.array(pointArb, { minLength: 2, maxLength: 10 });

describe('Feature: canvas-snap-to-grid, Property 3: Multi-select snap preserves relative positions', () => {
  it('relative displacements between all object pairs are preserved after snap-drag', () => {
    /**
     * **Validates: Requirements 2.2**
     *
     * Strategy:
     * 1. Generate N random positions (the "objects")
     * 2. Pick the first as "primary"
     * 3. Snap the primary position to grid using snapToGrid
     * 4. Compute delta = snapped_primary - original_primary
     * 5. Apply that delta to all other positions
     * 6. Verify that for any pair (i, j), the relative displacement
     *    (pos_i - pos_j) is the same before and after
     */
    fc.assert(
      fc.property(positionSetArb, gridSizeArb, (positions, gridSize) => {
        // Original positions
        const primary = positions[0];

        // Snap the primary to the grid
        const snappedPrimary: Point = {
          x: snapToGrid(primary.x, gridSize),
          y: snapToGrid(primary.y, gridSize),
        };

        // Compute the delta from snapping the primary
        const deltaX = snappedPrimary.x - primary.x;
        const deltaY = snappedPrimary.y - primary.y;

        // Apply the same delta to all positions (including primary)
        const newPositions: Point[] = positions.map((pos) => ({
          x: pos.x + deltaX,
          y: pos.y + deltaY,
        }));

        // For every pair (i, j), verify relative displacement is preserved
        for (let i = 0; i < positions.length; i++) {
          for (let j = i + 1; j < positions.length; j++) {
            const relBefore = {
              dx: positions[i].x - positions[j].x,
              dy: positions[i].y - positions[j].y,
            };
            const relAfter = {
              dx: newPositions[i].x - newPositions[j].x,
              dy: newPositions[i].y - newPositions[j].y,
            };

            expect(Math.abs(relAfter.dx - relBefore.dx)).toBeLessThan(1e-9);
            expect(Math.abs(relAfter.dy - relBefore.dy)).toBeLessThan(1e-9);
          }
        }
      }),
      { numRuns: 100 },
    );
  });
});
