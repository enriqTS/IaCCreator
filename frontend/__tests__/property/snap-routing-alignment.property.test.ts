/**
 * Property-based test: Grid-aware routing produces grid-aligned waypoints
 *
 * Feature: canvas-snap-to-grid, Property 7: Grid-aware routing produces grid-aligned waypoints
 *
 * **Validates: Requirements 5.1**
 *
 * For any start point, end point, start anchor position, end anchor position,
 * and valid grid cell size g, all waypoints returned by computeOrthogonalWaypoints
 * (when grid-aware) shall have both x and y coordinates that are multiples of g.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { computeOrthogonalWaypoints } from '@/utils/routing';
import type { AnchorPosition } from '@/utils/anchor';
import type { Point } from '@/types/diagram';

/** Arbitrary for valid grid cell sizes per the spec: integers in [5, 100]. */
const gridSizeArb = fc.integer({ min: 5, max: 100 });

/** Arbitrary for canvas coordinates across a reasonable range. */
const coordinateArb = fc.integer({ min: -5000, max: 5000 });

/** Arbitrary for a canvas Point with integer coordinates. */
const pointArb: fc.Arbitrary<Point> = fc.record({
  x: coordinateArb,
  y: coordinateArb,
});

/** Arbitrary for an anchor position. */
const anchorPositionArb: fc.Arbitrary<AnchorPosition> = fc.constantFrom(
  'top',
  'right',
  'bottom',
  'left',
);

describe('Feature: canvas-snap-to-grid, Property 7: Grid-aware routing produces grid-aligned waypoints', () => {
  it('all waypoints from computeOrthogonalWaypoints have coordinates that are multiples of gridSize', () => {
    /**
     * **Validates: Requirements 5.1**
     *
     * Strategy: Generate random start/end points, anchor positions, and grid sizes.
     * Call computeOrthogonalWaypoints with gridSize. Verify every waypoint's x and y
     * are exact multiples of the grid size.
     * Skip the degenerate case where start === end (returns []).
     */
    fc.assert(
      fc.property(
        pointArb,
        anchorPositionArb,
        pointArb,
        anchorPositionArb,
        gridSizeArb,
        (start, startPos, end, endPos, gridSize) => {
          // Skip degenerate case where start and end are the same point
          fc.pre(start.x !== end.x || start.y !== end.y);

          const waypoints = computeOrthogonalWaypoints(
            start,
            startPos,
            end,
            endPos,
            undefined,
            gridSize,
          );

          for (const wp of waypoints) {
            const remainderX = Math.abs(wp.x % gridSize);
            const isXAligned =
              remainderX < 1e-9 || Math.abs(remainderX - gridSize) < 1e-9;

            const remainderY = Math.abs(wp.y % gridSize);
            const isYAligned =
              remainderY < 1e-9 || Math.abs(remainderY - gridSize) < 1e-9;

            expect(isXAligned).toBe(true);
            expect(isYAligned).toBe(true);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
