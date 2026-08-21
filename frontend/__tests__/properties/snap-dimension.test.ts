/**
 * Property-based test: Dimension snapping produces grid-aligned dimensions with minimum
 *
 * Feature: canvas-snap-to-grid, Property 2: Dimension snapping produces grid-aligned dimensions with minimum
 *
 * **Validates: Requirements 1.2, 4.1, 4.2, 4.3**
 *
 * For any dimension value d > 0 and any valid grid cell size g (5 ≤ g ≤ 100),
 * snapDimension(d, g) returns a value that is a multiple of g and is at least g.
 * That is: snapDimension(d, g) % g === 0 and snapDimension(d, g) >= g.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { snapDimension } from '@/utils/snap';

/** Arbitrary for valid grid cell sizes per the spec: integers in [5, 100]. */
const gridSizeArb = fc.integer({ min: 5, max: 100 });

/** Arbitrary for positive dimension values across a wide range. */
const dimensionArb = fc.double({
  min: 0.01,
  max: 100000,
  noNaN: true,
  noDefaultInfinity: true,
});

describe('Feature: canvas-snap-to-grid, Property 2: Dimension snapping produces grid-aligned dimensions with minimum', () => {
  it('snapDimension(d, g) % g === 0 for any positive dimension d and valid grid size g', () => {
    /**
     * **Validates: Requirements 1.2, 4.1, 4.2, 4.3**
     *
     * Strategy: Generate random positive dimensions and grid sizes in [5, 100].
     * Verify that the snapped dimension is always an exact multiple of the grid size.
     */
    fc.assert(
      fc.property(dimensionArb, gridSizeArb, (dimension, gridSize) => {
        const snapped = snapDimension(dimension, gridSize);

        // The snapped dimension must be a multiple of gridSize.
        // Use a tolerance check for floating-point arithmetic.
        const remainder = Math.abs(snapped % gridSize);
        const isAligned = remainder < 1e-9 || Math.abs(remainder - gridSize) < 1e-9;

        expect(isAligned).toBe(true);
      }),
      { numRuns: 100 },
    );
  });

  it('snapDimension(d, g) >= g for any positive dimension d and valid grid size g', () => {
    /**
     * **Validates: Requirements 1.2, 4.1, 4.2, 4.3**
     *
     * Strategy: Generate random positive dimensions and grid sizes in [5, 100].
     * Verify that the snapped dimension is always at least one grid cell size,
     * enforcing the minimum size constraint.
     */
    fc.assert(
      fc.property(dimensionArb, gridSizeArb, (dimension, gridSize) => {
        const snapped = snapDimension(dimension, gridSize);

        expect(snapped).toBeGreaterThanOrEqual(gridSize);
      }),
      { numRuns: 100 },
    );
  });
});
