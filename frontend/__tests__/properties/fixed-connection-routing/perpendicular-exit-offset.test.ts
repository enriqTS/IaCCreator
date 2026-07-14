import fc from 'fast-check';
import { computeOrthogonalWaypoints } from '@/utils/routing/routing';
import type { AnchorPosition } from '@/utils/anchor';
import type { Point } from '@/types/diagram';

// Feature: fixed-connection-routing
// **Property 4: Orthogonal routes exit perpendicular with minimum offset**
// **Validates: Requirements 2.2, 2.6**
//
// IMPORTANT: Skip the degenerate case where start === end (empty waypoints)
// and skip Case 1 (facing anchors on shared axis) which by design returns
// zero waypoints — the offset property applies to routes with waypoints.

const ANCHOR_POSITIONS: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

function pointArbitrary(): fc.Arbitrary<Point> {
  return fc.record({
    x: fc.integer({ min: -2000, max: 2000 }),
    y: fc.integer({ min: -2000, max: 2000 }),
  });
}

function anchorPositionArbitrary(): fc.Arbitrary<AnchorPosition> {
  return fc.constantFrom(...ANCHOR_POSITIONS);
}

function minOffsetArbitrary(): fc.Arbitrary<number> {
  return fc.integer({ min: 1, max: 100 });
}

/**
 * Compute the signed displacement in the outward direction for a given anchor position.
 * top → negative Y, right → positive X, bottom → positive Y, left → negative X
 */
function outwardDisplacement(from: Point, to: Point, position: AnchorPosition): number {
  switch (position) {
    case 'top': return from.y - to.y;     // negative Y means upward
    case 'right': return to.x - from.x;   // positive X means rightward
    case 'bottom': return to.y - from.y;   // positive Y means downward
    case 'left': return from.x - to.x;     // negative X means leftward
  }
}

describe('Property 4: Orthogonal routes exit perpendicular with minimum offset', () => {
  test('the first segment extends at least minOffset in the outward direction of the source anchor, and the last segment extends at least minOffset in the outward direction of the target anchor', () => {
    fc.assert(
      fc.property(
        pointArbitrary(),
        anchorPositionArbitrary(),
        pointArbitrary(),
        anchorPositionArbitrary(),
        minOffsetArbitrary(),
        (start, startPos, end, endPos, minOffset) => {
          // Skip the degenerate case where start === end (empty waypoints)
          fc.pre(start.x !== end.x || start.y !== end.y);

          const waypoints = computeOrthogonalWaypoints(start, startPos, end, endPos, minOffset);

          // Skip Case 1 (facing anchors, aligned) which returns zero waypoints by design.
          // The offset property applies to routes that have waypoints.
          fc.pre(waypoints.length > 0);

          const path = [start, ...waypoints, end];

          // First segment: start → path[1]
          const firstNext = path[1];
          const sourceDisplacement = outwardDisplacement(start, firstNext, startPos);
          expect(sourceDisplacement).toBeGreaterThanOrEqual(minOffset - 1e-9);

          // Last segment: path[path.length - 2] → end
          const lastPrev = path[path.length - 2];
          const targetDisplacement = outwardDisplacement(end, lastPrev, endPos);
          expect(targetDisplacement).toBeGreaterThanOrEqual(minOffset - 1e-9);
        },
      ),
      { numRuns: 200 },
    );
  });
});
