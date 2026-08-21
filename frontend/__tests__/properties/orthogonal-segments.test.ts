/**
 * Property-based test: Orthogonal routing produces only horizontal and vertical segments
 *
 * Feature: line-segment-manipulation, Property 2: Orthogonal routing produces only horizontal and vertical segments
 *
 * **Validates: Requirements 2.1, 2.2**
 *
 * For any two distinct points (start, end) and any combination of anchor configurations
 * (both anchored, one anchored, neither anchored), when routingMode is 'orthogonal',
 * every consecutive pair of points in the resulting path forms either a horizontal
 * segment (same y) or a vertical segment (same x).
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { computeOrthogonalWaypoints, inferAnchorPosition } from '@/utils/routing/routing';
import type { AnchorPosition } from '@/utils/anchor';
import type { Point } from '@/types/diagram';

/** Arbitrary for coordinate values across a wide range. */
const coordArb = fc.integer({ min: -5000, max: 5000 });

/** Arbitrary for a Point. */
const pointArb: fc.Arbitrary<Point> = fc.record({ x: coordArb, y: coordArb });

/** Arbitrary for an anchor position. */
const anchorPositionArb: fc.Arbitrary<AnchorPosition> = fc.constantFrom(
  'top',
  'right',
  'bottom',
  'left',
);

/**
 * Helper: build the full path [start, ...waypoints, end] and verify every
 * consecutive pair is either horizontal (same y) or vertical (same x).
 */
function assertAllSegmentsOrthogonal(start: Point, waypoints: Point[], end: Point): void {
  const path = [start, ...waypoints, end];
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i];
    const b = path[i + 1];
    const isHorizontal = a.y === b.y;
    const isVertical = a.x === b.x;
    expect(
      isHorizontal || isVertical,
      `Segment ${i} from (${a.x},${a.y}) to (${b.x},${b.y}) is neither horizontal nor vertical`,
    ).toBe(true);
  }
}

describe('Feature: line-segment-manipulation, Property 2: Orthogonal routing produces only horizontal and vertical segments', () => {
  it('produces only H/V segments with explicit anchor positions on both ends', () => {
    /**
     * **Validates: Requirements 2.1, 2.2**
     *
     * Both endpoints have explicit anchor positions. Generate random start/end
     * points and anchor positions, compute waypoints, build the full path, and
     * verify each consecutive pair is horizontal or vertical.
     */
    fc.assert(
      fc.property(
        pointArb,
        anchorPositionArb,
        pointArb,
        anchorPositionArb,
        (start, startPos, end, endPos) => {
          fc.pre(start.x !== end.x || start.y !== end.y);

          const waypoints = computeOrthogonalWaypoints(start, startPos, end, endPos);
          assertAllSegmentsOrthogonal(start, waypoints, end);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('produces only H/V segments with inferred anchor positions (both unanchored)', () => {
    /**
     * **Validates: Requirements 2.1, 2.2**
     *
     * Neither endpoint is anchored. Infer anchor positions from geometry,
     * compute waypoints, and verify all segments are orthogonal.
     */
    fc.assert(
      fc.property(pointArb, pointArb, (start, end) => {
        fc.pre(start.x !== end.x || start.y !== end.y);

        const startPos = inferAnchorPosition(start, end);
        const endPos = inferAnchorPosition(end, start);
        const waypoints = computeOrthogonalWaypoints(start, startPos, end, endPos);
        assertAllSegmentsOrthogonal(start, waypoints, end);
      }),
      { numRuns: 100 },
    );
  });

  it('produces only H/V segments with one anchored and one inferred endpoint', () => {
    /**
     * **Validates: Requirements 2.1, 2.2**
     *
     * One endpoint has an explicit anchor position, the other infers it.
     * Verify all segments are orthogonal in both configurations.
     */
    fc.assert(
      fc.property(
        pointArb,
        anchorPositionArb,
        pointArb,
        (start, startPos, end) => {
          fc.pre(start.x !== end.x || start.y !== end.y);

          // Source anchored, target inferred
          const endPos = inferAnchorPosition(end, start);
          const waypoints = computeOrthogonalWaypoints(start, startPos, end, endPos);
          assertAllSegmentsOrthogonal(start, waypoints, end);
        },
      ),
      { numRuns: 100 },
    );
  });
});
