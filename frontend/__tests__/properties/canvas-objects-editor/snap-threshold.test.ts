import fc from 'fast-check';
import { describe, it, expect } from 'vitest';
import { findSnapAnchor, getAnchorPoints, SNAP_THRESHOLD } from '@/utils/anchor';
import type { Point, Rect } from '@/types/diagram';

/**
 * Arbitrary for a rectangle with positive width and height.
 */
function rectArbitrary(): fc.Arbitrary<Rect> {
  return fc.record({
    x: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
    y: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
    width: fc.double({ min: 1, max: 2000, noNaN: true, noDefaultInfinity: true }),
    height: fc.double({ min: 1, max: 2000, noNaN: true, noDefaultInfinity: true }),
  });
}

/**
 * Arbitrary for a random point in canvas space.
 */
function pointArbitrary(): fc.Arbitrary<Point> {
  return fc.record({
    x: fc.double({ min: -10000, max: 10000, noNaN: true, noDefaultInfinity: true }),
    y: fc.double({ min: -10000, max: 10000, noNaN: true, noDefaultInfinity: true }),
  });
}

/**
 * Arbitrary for a positive threshold value.
 */
function thresholdArbitrary(): fc.Arbitrary<number> {
  return fc.double({ min: 1, max: 200, noNaN: true, noDefaultInfinity: true });
}

/** Euclidean distance between two points */
function distance(a: Point, b: Point): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
}

/** Minimum distance from a point to any of the 4 cardinal anchors */
function minDistToAnchors(point: Point, bounds: Rect): number {
  const anchors = getAnchorPoints(bounds);
  const anchorList = Object.values(anchors) as Point[];
  let minDist = Infinity;
  for (const anchor of anchorList) {
    const d = distance(point, anchor);
    if (d < minDist) minDist = d;
  }
  return minDist;
}

// Feature: canvas-objects-editor, Property 3: Snap threshold boundary
// **Validates: Requirements 2.2**
describe('Property 3: Snap threshold boundary', () => {
  it('returns non-null if and only if the point is within threshold of a cardinal anchor', () => {
    fc.assert(
      fc.property(
        rectArbitrary(),
        pointArbitrary(),
        thresholdArbitrary(),
        (bounds, point, threshold) => {
          const result = findSnapAnchor(point, bounds, threshold);
          const minDist = minDistToAnchors(point, bounds);

          if (minDist <= threshold) {
            // Point is within threshold of at least one anchor → must snap
            expect(result).not.toBeNull();
          } else {
            // Point is beyond threshold of all anchors → must not snap
            expect(result).toBeNull();
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('returned anchor is always one of the 4 cardinal anchor points', () => {
    fc.assert(
      fc.property(
        rectArbitrary(),
        pointArbitrary(),
        thresholdArbitrary(),
        (bounds, point, threshold) => {
          const result = findSnapAnchor(point, bounds, threshold);

          if (result !== null) {
            const anchors = getAnchorPoints(bounds);
            const anchorList = Object.values(anchors) as Point[];
            const matchesAnchor = anchorList.some(
              (a) => a.x === result.x && a.y === result.y
            );
            expect(matchesAnchor).toBe(true);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('uses SNAP_THRESHOLD as default when no threshold argument is provided', () => {
    fc.assert(
      fc.property(
        rectArbitrary(),
        pointArbitrary(),
        (bounds, point) => {
          const resultDefault = findSnapAnchor(point, bounds);
          const resultExplicit = findSnapAnchor(point, bounds, SNAP_THRESHOLD);

          // Both calls should produce the same result
          if (resultDefault === null) {
            expect(resultExplicit).toBeNull();
          } else {
            expect(resultExplicit).not.toBeNull();
            expect(resultDefault!.x).toBe(resultExplicit!.x);
            expect(resultDefault!.y).toBe(resultExplicit!.y);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
