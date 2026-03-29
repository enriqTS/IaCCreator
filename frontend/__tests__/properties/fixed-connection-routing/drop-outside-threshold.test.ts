import fc from 'fast-check';
import {
  findSnapAnchorWithPosition,
  getAnchorPoints,
  SNAP_THRESHOLD,
} from '@/utils/anchor';
import type { AnchorPosition } from '@/utils/anchor';
import type { Point, Rect } from '@/types/diagram';

// Feature: fixed-connection-routing
// **Property 8: Drop outside snap threshold creates free-floating line**
// **Validates: Requirements 6.3**

/**
 * Generates a random Rect with positive width/height and reasonable coordinates.
 */
function rectArbitrary(): fc.Arbitrary<Rect> {
  return fc.record({
    x: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
    y: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
    width: fc.double({ min: 10, max: 500, noNaN: true, noDefaultInfinity: true }),
    height: fc.double({ min: 10, max: 500, noNaN: true, noDefaultInfinity: true }),
  });
}

const ANCHOR_POSITIONS: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

/**
 * Generates a point guaranteed to be farther than SNAP_THRESHOLD from all 4 anchor
 * points of the given rect. Strategy: pick a random anchor, then offset it by more
 * than SNAP_THRESHOLD in a random direction. Then verify the point is far enough from
 * all anchors (pre-condition filter).
 */
function pointOutsideThresholdArbitrary(rect: Rect): fc.Arbitrary<Point> {
  const anchors = getAnchorPoints(rect);
  return fc
    .record({
      anchorPos: fc.constantFrom<AnchorPosition>(...ANCHOR_POSITIONS),
      angle: fc.double({ min: 0, max: Math.PI * 2, noNaN: true, noDefaultInfinity: true }),
      // Distance strictly greater than SNAP_THRESHOLD — add a margin to avoid floating-point edge
      extraDist: fc.double({ min: 1, max: 500, noNaN: true, noDefaultInfinity: true }),
    })
    .map(({ anchorPos, angle, extraDist }) => {
      const anchor = anchors[anchorPos];
      const distance = SNAP_THRESHOLD + extraDist;
      return {
        x: anchor.x + Math.cos(angle) * distance,
        y: anchor.y + Math.sin(angle) * distance,
      };
    })
    .filter((point) => {
      // Ensure the generated point is farther than SNAP_THRESHOLD from ALL anchors
      for (const pos of ANCHOR_POSITIONS) {
        const anchor = anchors[pos];
        const dx = point.x - anchor.x;
        const dy = point.y - anchor.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist <= SNAP_THRESHOLD) {
          return false;
        }
      }
      return true;
    });
}

describe('Property 8: Drop outside snap threshold creates free-floating line', () => {
  test('for any drop point farther than snap threshold from all anchors, findSnapAnchorWithPosition returns null', () => {
    fc.assert(
      fc.property(
        rectArbitrary().chain((rect) =>
          pointOutsideThresholdArbitrary(rect).map((point) => ({ rect, point })),
        ),
        ({ rect, point }) => {
          const result = findSnapAnchorWithPosition(point, rect);
          expect(result).toBeNull();
        },
      ),
      { numRuns: 200 },
    );
  });
});
