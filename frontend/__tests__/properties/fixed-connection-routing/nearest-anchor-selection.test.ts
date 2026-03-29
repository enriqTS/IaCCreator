import fc from 'fast-check';
import {
  findSnapAnchorWithPosition,
  getAnchorPoints,
  SNAP_THRESHOLD,
} from '@/utils/anchor';
import type { AnchorPosition } from '@/utils/anchor';
import type { Point, Rect } from '@/types/diagram';

// Feature: fixed-connection-routing
// **Property 1: Nearest anchor selection**
// **Validates: Requirements 1.3, 6.2**

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
 * Generates a random AnchorPosition.
 */
function anchorPositionArbitrary(): fc.Arbitrary<AnchorPosition> {
  return fc.constantFrom(...ANCHOR_POSITIONS);
}

/**
 * Euclidean distance between two points.
 */
function euclideanDist(a: Point, b: Point): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
}

describe('Property 1: Nearest anchor selection', () => {
  test('for any bounding rect and external point within snap threshold, findSnapAnchorWithPosition returns the anchor position with the smallest Euclidean distance to the point', () => {
    fc.assert(
      fc.property(
        rectArbitrary(),
        anchorPositionArbitrary(),
        // Random angle and distance within snap threshold to offset from the chosen anchor
        fc.double({ min: 0, max: Math.PI * 2, noNaN: true, noDefaultInfinity: true }),
        fc.double({ min: 0, max: SNAP_THRESHOLD * 0.99, noNaN: true, noDefaultInfinity: true }),
        (rect, anchorPos, angle, distance) => {
          const anchors = getAnchorPoints(rect);
          const chosenAnchor = anchors[anchorPos];

          // Generate a point within snap threshold of the chosen anchor
          const testPoint: Point = {
            x: chosenAnchor.x + Math.cos(angle) * distance,
            y: chosenAnchor.y + Math.sin(angle) * distance,
          };

          const result = findSnapAnchorWithPosition(testPoint, rect);

          // The result must not be null since we're within threshold
          expect(result).not.toBeNull();

          // The returned position must be the geometrically closest anchor
          const returnedDist = euclideanDist(testPoint, result!.point);

          for (const pos of ANCHOR_POSITIONS) {
            const anchorPoint = anchors[pos];
            const dist = euclideanDist(testPoint, anchorPoint);
            // The returned anchor's distance should be <= every other anchor's distance
            expect(returnedDist).toBeLessThanOrEqual(dist + 1e-9);
          }

          // The returned point should match the anchor at the returned position
          const expectedPoint = anchors[result!.position];
          expect(result!.point.x).toBeCloseTo(expectedPoint.x, 5);
          expect(result!.point.y).toBeCloseTo(expectedPoint.y, 5);
        },
      ),
      { numRuns: 200 },
    );
  });
});
