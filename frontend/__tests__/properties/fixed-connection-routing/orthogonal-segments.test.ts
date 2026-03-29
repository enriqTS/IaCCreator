import fc from 'fast-check';
import { computeOrthogonalWaypoints } from '@/utils/routing';
import type { AnchorPosition } from '@/utils/anchor';
import type { Point } from '@/types/diagram';

// Feature: fixed-connection-routing
// **Property 3: Orthogonal routes contain only horizontal and vertical segments**
// **Validates: Requirements 2.1, 2.4**

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

/** Build the full path: start + waypoints + end */
function fullPath(start: Point, waypoints: Point[], end: Point): Point[] {
  return [start, ...waypoints, end];
}

describe('Property 3: Orthogonal routes contain only horizontal and vertical segments', () => {
  test('for any start/end points with anchor positions, every consecutive pair in the full path shares the same X or same Y coordinate', () => {
    fc.assert(
      fc.property(
        pointArbitrary(),
        anchorPositionArbitrary(),
        pointArbitrary(),
        anchorPositionArbitrary(),
        (start, startPos, end, endPos) => {
          const waypoints = computeOrthogonalWaypoints(start, startPos, end, endPos);
          const path = fullPath(start, waypoints, end);

          for (let i = 0; i < path.length - 1; i++) {
            const a = path[i];
            const b = path[i + 1];
            const sameX = a.x === b.x;
            const sameY = a.y === b.y;
            expect(
              sameX || sameY,
              `Segment ${i}: (${a.x},${a.y})→(${b.x},${b.y}) is not axis-aligned`,
            ).toBe(true);
          }
        },
      ),
      { numRuns: 200 },
    );
  });
});
