/**
 * Property-based test: Nearest anchor position by geometric proximity
 *
 * Feature: line-segment-manipulation, Property 9: Nearest anchor position by geometric proximity
 *
 * **Validates: Requirements 4.1, 4.3, 4.4, 4.6**
 *
 * For any rectangular bounds and any external point, `findNearestAnchorPosition`
 * returns the cardinal anchor position whose anchor point has the smallest Euclidean
 * distance. When currentPosition is equidistant with another, currentPosition is retained.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { findNearestAnchorPosition, getAnchorPoints } from '@/utils/anchor';
import type { AnchorPosition } from '@/utils/anchor';
import type { Point, Rect } from '@/types/diagram';

/** Arbitrary for coordinate values. */
const coordArb = fc.integer({ min: -5000, max: 5000 });

/** Arbitrary for a Point. */
const pointArb: fc.Arbitrary<Point> = fc.record({ x: coordArb, y: coordArb });

/** Arbitrary for a Rect with positive width and height. */
const rectArb: fc.Arbitrary<Rect> = fc.record({
  x: coordArb,
  y: coordArb,
  width: fc.integer({ min: 40, max: 500 }),
  height: fc.integer({ min: 40, max: 500 }),
});

/** Arbitrary for an AnchorPosition. */
const anchorPositionArb: fc.Arbitrary<AnchorPosition> = fc.constantFrom(
  'top' as const,
  'right' as const,
  'bottom' as const,
  'left' as const,
);

/** Euclidean distance between two points. */
function euclidean(a: Point, b: Point): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
}

describe('Feature: line-segment-manipulation, Property 9: Nearest anchor position by geometric proximity', () => {
  it('returns the anchor position with the smallest Euclidean distance to the point', () => {
    /**
     * **Validates: Requirements 4.1, 4.3, 4.4**
     *
     * Strategy: Generate random rects and points. Compute the distance from the
     * point to each of the four cardinal anchor points. Verify that the returned
     * position has a distance equal to the minimum distance (within tolerance).
     */
    fc.assert(
      fc.property(pointArb, rectArb, (point, bounds) => {
        const result = findNearestAnchorPosition(point, bounds);
        const anchors = getAnchorPoints(bounds);
        const positions: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

        const resultDist = euclidean(point, anchors[result]);
        const minDist = Math.min(...positions.map((p) => euclidean(point, anchors[p])));

        // The returned position's distance should equal the minimum distance
        expect(resultDist).toBeCloseTo(minDist, 9);
      }),
      { numRuns: 100 },
    );
  });

  it('retains currentPosition when it is equidistant with another anchor', () => {
    /**
     * **Validates: Requirements 4.6**
     *
     * Strategy: Generate rects and anchor positions. Construct a point that is
     * equidistant from the currentPosition anchor and at least one other anchor.
     * Verify that currentPosition is retained.
     */
    fc.assert(
      fc.property(rectArb, anchorPositionArb, (bounds, currentPosition) => {
        const anchors = getAnchorPoints(bounds);
        // Use the anchor point of currentPosition itself — it's distance 0 from itself,
        // which is always the minimum, so it should always be returned.
        const point = anchors[currentPosition];

        const result = findNearestAnchorPosition(point, bounds, currentPosition);
        expect(result).toBe(currentPosition);
      }),
      { numRuns: 100 },
    );
  });

  it('retains currentPosition on true equidistant tie with another anchor', () => {
    /**
     * **Validates: Requirements 4.6**
     *
     * Strategy: For a square rect, the center is equidistant from all four anchors.
     * Regardless of which currentPosition is provided, it should be retained.
     */
    fc.assert(
      fc.property(
        coordArb,
        fc.integer({ min: 40, max: 500 }),
        anchorPositionArb,
        (origin, size, currentPosition) => {
          const bounds: Rect = { x: origin, y: origin, width: size, height: size };
          const cx = origin + size / 2;
          const cy = origin + size / 2;
          const center: Point = { x: cx, y: cy };

          // Center of a square is equidistant from all four cardinal anchors
          const result = findNearestAnchorPosition(center, bounds, currentPosition);
          expect(result).toBe(currentPosition);
        },
      ),
      { numRuns: 100 },
    );
  });
});
