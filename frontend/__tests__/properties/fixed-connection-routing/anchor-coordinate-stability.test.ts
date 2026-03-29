import fc from 'fast-check';
import { getAnchorPoints } from '@/utils/anchor';
import type { AnchorPosition } from '@/utils/anchor';
import type { Rect } from '@/types/diagram';

// Feature: fixed-connection-routing
// **Property 2: Anchor coordinate computation is stable across moves**
// **Validates: Requirements 1.4, 1.5, 3.2**

const ANCHOR_POSITIONS: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

function rectArbitrary(): fc.Arbitrary<Rect> {
  return fc.record({
    x: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
    y: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
    width: fc.double({ min: 10, max: 500, noNaN: true, noDefaultInfinity: true }),
    height: fc.double({ min: 10, max: 500, noNaN: true, noDefaultInfinity: true }),
  });
}

function anchorPositionArbitrary(): fc.Arbitrary<AnchorPosition> {
  return fc.constantFrom(...ANCHOR_POSITIONS);
}

function translationArbitrary(): fc.Arbitrary<{ dx: number; dy: number }> {
  return fc.record({
    dx: fc.double({ min: -1000, max: 1000, noNaN: true, noDefaultInfinity: true }),
    dy: fc.double({ min: -1000, max: 1000, noNaN: true, noDefaultInfinity: true }),
  });
}

/** Compute the expected center-of-side coordinate for a given anchor position */
function expectedAnchorCoord(rect: Rect, pos: AnchorPosition): { x: number; y: number } {
  const cx = rect.x + rect.width / 2;
  const cy = rect.y + rect.height / 2;
  switch (pos) {
    case 'top': return { x: cx, y: rect.y };
    case 'right': return { x: rect.x + rect.width, y: cy };
    case 'bottom': return { x: cx, y: rect.y + rect.height };
    case 'left': return { x: rect.x, y: cy };
  }
}

describe('Property 2: Anchor coordinate computation is stable across moves', () => {
  test('for any rect and anchor position, the computed coordinate equals the center of that side', () => {
    fc.assert(
      fc.property(
        rectArbitrary(),
        anchorPositionArbitrary(),
        (rect, pos) => {
          const anchors = getAnchorPoints(rect);
          const actual = anchors[pos];
          const expected = expectedAnchorCoord(rect, pos);

          expect(actual.x).toBeCloseTo(expected.x, 5);
          expect(actual.y).toBeCloseTo(expected.y, 5);
        },
      ),
      { numRuns: 100 },
    );
  });

  test('after translation (dx, dy), the position value is unchanged and the coordinate equals the center of the translated side', () => {
    fc.assert(
      fc.property(
        rectArbitrary(),
        anchorPositionArbitrary(),
        translationArbitrary(),
        (rect, pos, { dx, dy }) => {
          // Original anchor
          const anchorsBefore = getAnchorPoints(rect);
          const coordBefore = anchorsBefore[pos];

          // Translate the rect
          const translatedRect: Rect = {
            x: rect.x + dx,
            y: rect.y + dy,
            width: rect.width,
            height: rect.height,
          };

          // Recompute anchors on translated rect
          const anchorsAfter = getAnchorPoints(translatedRect);
          const coordAfter = anchorsAfter[pos];

          // The position value (pos) is unchanged — same key used
          // The coordinate equals the center of the translated side
          const expectedAfter = expectedAnchorCoord(translatedRect, pos);
          expect(coordAfter.x).toBeCloseTo(expectedAfter.x, 5);
          expect(coordAfter.y).toBeCloseTo(expectedAfter.y, 5);

          // The coordinate shifted by exactly (dx, dy)
          expect(coordAfter.x).toBeCloseTo(coordBefore.x + dx, 5);
          expect(coordAfter.y).toBeCloseTo(coordBefore.y + dy, 5);
        },
      ),
      { numRuns: 100 },
    );
  });
});
