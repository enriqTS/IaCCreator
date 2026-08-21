/**
 * Property-based test: Grid snapping produces grid-aligned coordinates
 *
 * Feature: canvas-snap-to-grid, Property 1: Grid snapping produces grid-aligned coordinates
 *
 * **Validates: Requirements 1.1, 2.1, 2.3, 5.2**
 *
 * For any coordinate value v and any valid grid cell size g (5 ≤ g ≤ 100),
 * snapToGrid(v, g) returns a value that is a multiple of g.
 * For snapPointToGrid(point, g), both result.x and result.y are multiples of g.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { snapToGrid, snapPointToGrid } from '@/utils/snap';
import type { Point } from '@/types/diagram';

/** Arbitrary for valid grid cell sizes per the spec: integers in [5, 100]. */
const gridSizeArb = fc.integer({ min: 5, max: 100 });

/** Arbitrary for coordinate values across a wide range. */
const coordinateArb = fc.double({
  min: -100000,
  max: 100000,
  noNaN: true,
  noDefaultInfinity: true,
});

/** Arbitrary for a canvas Point with reasonable coordinates. */
const pointArb: fc.Arbitrary<Point> = fc.record({
  x: coordinateArb,
  y: coordinateArb,
});

describe('Feature: canvas-snap-to-grid, Property 1: Grid snapping produces grid-aligned coordinates', () => {
  it('snapToGrid(v, g) % g === 0 for any coordinate v and valid grid size g', () => {
    /**
     * **Validates: Requirements 1.1, 2.1, 2.3, 5.2**
     *
     * Strategy: Generate random coordinates and grid sizes in [5, 100].
     * Verify that the snapped value is always an exact multiple of the grid size.
     */
    fc.assert(
      fc.property(coordinateArb, gridSizeArb, (value, gridSize) => {
        const snapped = snapToGrid(value, gridSize);

        // The snapped value must be a multiple of gridSize.
        // Use a tolerance check for floating-point arithmetic.
        const remainder = Math.abs(snapped % gridSize);
        const isAligned = remainder < 1e-9 || Math.abs(remainder - gridSize) < 1e-9;

        expect(isAligned).toBe(true);
      }),
      { numRuns: 100 },
    );
  });

  it('snapPointToGrid aligns both x and y to grid multiples', () => {
    /**
     * **Validates: Requirements 1.1, 2.1, 2.3, 5.2**
     *
     * Strategy: Generate random Points and grid sizes.
     * Verify that both result.x % g === 0 and result.y % g === 0.
     */
    fc.assert(
      fc.property(pointArb, gridSizeArb, (point, gridSize) => {
        const snapped = snapPointToGrid(point, gridSize);

        const remainderX = Math.abs(snapped.x % gridSize);
        const isXAligned = remainderX < 1e-9 || Math.abs(remainderX - gridSize) < 1e-9;

        const remainderY = Math.abs(snapped.y % gridSize);
        const isYAligned = remainderY < 1e-9 || Math.abs(remainderY - gridSize) < 1e-9;

        expect(isXAligned).toBe(true);
        expect(isYAligned).toBe(true);
      }),
      { numRuns: 100 },
    );
  });
});
