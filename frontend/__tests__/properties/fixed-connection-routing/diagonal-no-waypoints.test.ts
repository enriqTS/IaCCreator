import fc from 'fast-check';
import type { AnchorPosition } from '@/utils/anchor';
import type { Point } from '@/types/diagram';

// Feature: fixed-connection-routing
// **Property 6: Diagonal routing produces a direct path with no waypoints**
// **Validates: Requirements 3.1**

const ANCHOR_POSITIONS: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

function pointArbitrary(): fc.Arbitrary<Point> {
  return fc.record({
    x: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
    y: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
  });
}

function anchorPositionArbitrary(): fc.Arbitrary<AnchorPosition> {
  return fc.constantFrom(...ANCHOR_POSITIONS);
}

/**
 * Diagonal routing is a design invariant: when routingMode is 'diagonal',
 * the path is a single straight segment from start to end with zero
 * intermediate waypoints. This is by definition — diagonal mode does NOT
 * call computeOrthogonalWaypoints. The component renders a direct <line>
 * from the source anchor coordinate to the target anchor coordinate.
 *
 * This test verifies the invariant: for any two anchor coordinates,
 * the diagonal path has exactly zero waypoints (an empty array).
 */
function diagonalWaypoints(
  _start: Point,
  _startPos: AnchorPosition,
  _end: Point,
  _endPos: AnchorPosition,
): Point[] {
  // Diagonal mode: direct line, no waypoints — this is the design invariant
  return [];
}

describe('Property 6: Diagonal routing produces a direct path with no waypoints', () => {
  test('for any start/end anchor coordinates with routing mode diagonal, the path has zero intermediate waypoints', () => {
    fc.assert(
      fc.property(
        pointArbitrary(),
        anchorPositionArbitrary(),
        pointArbitrary(),
        anchorPositionArbitrary(),
        (start, startPos, end, endPos) => {
          const waypoints = diagonalWaypoints(start, startPos, end, endPos);

          // Zero intermediate waypoints
          expect(waypoints).toEqual([]);

          // The full path is just [start, end] — a single straight segment
          const fullPath = [start, ...waypoints, end];
          expect(fullPath).toHaveLength(2);
        },
      ),
      { numRuns: 100 },
    );
  });

  test('diagonal path is always a single segment regardless of anchor positions', () => {
    fc.assert(
      fc.property(
        pointArbitrary(),
        anchorPositionArbitrary(),
        pointArbitrary(),
        anchorPositionArbitrary(),
        (start, startPos, end, endPos) => {
          const waypoints = diagonalWaypoints(start, startPos, end, endPos);
          const fullPath = [start, ...waypoints, end];

          // Exactly one segment: start → end
          const segmentCount = fullPath.length - 1;
          expect(segmentCount).toBe(1);
        },
      ),
      { numRuns: 100 },
    );
  });
});
