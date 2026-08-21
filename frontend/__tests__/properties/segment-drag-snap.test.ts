/**
 * Property-based test: Segment drag snaps to grid when enabled
 *
 * Feature: line-segment-manipulation, Property 6: Segment drag snaps to grid when enabled
 *
 * **Validates: Requirements 3.5**
 *
 * For any segment position and any valid grid cell size, when snap-to-grid is enabled,
 * the resulting segment coordinate is a multiple of the grid cell size.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { snapToGrid } from '@/utils/snap';

/** Arbitrary for valid grid cell sizes per the spec: integers in [5, 100]. */
const gridSizeArb = fc.integer({ min: 5, max: 100 });

/** Arbitrary for segment coordinate values across a wide range. */
const coordinateArb = fc.double({
  min: -10000,
  max: 10000,
  noNaN: true,
  noDefaultInfinity: true,
});

describe('Feature: line-segment-manipulation, Property 6: Segment drag snaps to grid when enabled', () => {
  it('snapToGrid produces a value that is a multiple of the grid cell size for any segment coordinate', () => {
    /**
     * **Validates: Requirements 3.5**
     *
     * Strategy: Generate random segment coordinates and grid sizes.
     * Apply snapToGrid to the coordinate. Verify the result is a multiple
     * of the grid size (within floating-point tolerance).
     */
    fc.assert(
      fc.property(coordinateArb, gridSizeArb, (coordinate, gridSize) => {
        const snapped = snapToGrid(coordinate, gridSize);

        // The snapped value must be a multiple of gridSize.
        const remainder = Math.abs(snapped % gridSize);
        const isAligned = remainder < 1e-9 || Math.abs(remainder - gridSize) < 1e-9;

        expect(isAligned).toBe(true);
      }),
      { numRuns: 100 },
    );
  });

  it('snapToGrid returns the nearest grid line to the original coordinate', () => {
    /**
     * **Validates: Requirements 3.5**
     *
     * Strategy: For any coordinate and grid size, the snapped value should be
     * the closest grid multiple. Verify that the distance from the original
     * coordinate to the snapped value is at most half the grid size.
     */
    fc.assert(
      fc.property(coordinateArb, gridSizeArb, (coordinate, gridSize) => {
        const snapped = snapToGrid(coordinate, gridSize);
        const distance = Math.abs(snapped - coordinate);

        // The snapped value should be within half a grid cell of the original
        expect(distance).toBeLessThanOrEqual(gridSize / 2 + 1e-9);
      }),
      { numRuns: 100 },
    );
  });

  it('applying snapToGrid to an already-snapped coordinate returns the same value', () => {
    /**
     * **Validates: Requirements 3.5**
     *
     * Strategy: Snap a coordinate, then snap the result again. The value
     * should be idempotent — snapping an already-snapped value produces
     * the same result.
     */
    fc.assert(
      fc.property(coordinateArb, gridSizeArb, (coordinate, gridSize) => {
        const snapped = snapToGrid(coordinate, gridSize);
        const snappedAgain = snapToGrid(snapped, gridSize);

        expect(snappedAgain).toBe(snapped);
      }),
      { numRuns: 100 },
    );
  });
});
