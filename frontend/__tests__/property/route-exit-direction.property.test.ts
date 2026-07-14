/**
 * Property-based test: Route exits perpendicular to anchor side
 *
 * Feature: line-segment-manipulation, Property 10: Route exits perpendicular to anchor side
 *
 * **Validates: Requirements 4.2**
 *
 * For any anchored line endpoint, the first segment from that endpoint exits in the
 * direction perpendicular to the anchor side: top → upward (decreasing y),
 * right → rightward (increasing x), bottom → downward (increasing y),
 * left → leftward (decreasing x).
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { computeOrthogonalWaypoints } from '@/utils/routing/routing';
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
 * Check that the direction from `from` to `to` matches the expected exit
 * direction for the given anchor position.
 *
 * top    → dy < 0 (upward),    dx === 0
 * right  → dx > 0 (rightward), dy === 0
 * bottom → dy > 0 (downward),  dx === 0
 * left   → dx < 0 (leftward),  dy === 0
 *
 * When from === to (zero-length first segment), the direction is trivially
 * satisfied so we skip the check.
 */
function assertExitDirection(
  from: Point,
  to: Point,
  anchorPosition: AnchorPosition,
): void {
  const dx = to.x - from.x;
  const dy = to.y - from.y;

  // Zero-length segment — no direction to verify
  if (dx === 0 && dy === 0) return;

  switch (anchorPosition) {
    case 'top':
      // Must exit upward: dy <= 0 and dx === 0
      expect(dy).toBeLessThanOrEqual(0);
      expect(dx).toBe(0);
      break;
    case 'right':
      // Must exit rightward: dx >= 0 and dy === 0
      expect(dx).toBeGreaterThanOrEqual(0);
      expect(dy).toBe(0);
      break;
    case 'bottom':
      // Must exit downward: dy >= 0 and dx === 0
      expect(dy).toBeGreaterThanOrEqual(0);
      expect(dx).toBe(0);
      break;
    case 'left':
      // Must exit leftward: dx <= 0 and dy === 0
      expect(dx).toBeLessThanOrEqual(0);
      expect(dy).toBe(0);
      break;
  }
}

describe('Feature: line-segment-manipulation, Property 10: Route exits perpendicular to anchor side', () => {
  it('start endpoint exits in the direction perpendicular to its anchor side', () => {
    /**
     * **Validates: Requirements 4.2**
     *
     * Generate random start/end points with explicit anchor positions.
     * Compute waypoints. The first segment goes from start to the first
     * waypoint (or to end if no waypoints). Verify the exit direction
     * matches the start anchor position.
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
          const firstTarget = waypoints.length > 0 ? waypoints[0] : end;
          assertExitDirection(start, firstTarget, startPos);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('end endpoint exits in the direction perpendicular to its anchor side', () => {
    /**
     * **Validates: Requirements 4.2**
     *
     * Same approach but checking the last segment: from the last waypoint
     * (or start if no waypoints) to end. The direction into end should be
     * the opposite of the end anchor's exit direction, meaning the segment
     * arriving at end comes from the exit direction of the end anchor.
     * Equivalently, from end toward the last waypoint should match the
     * end anchor's exit direction.
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
          const lastSource = waypoints.length > 0 ? waypoints[waypoints.length - 1] : start;

          // The last segment goes from lastSource → end.
          // From end's perspective, the route exits end in the endPos direction,
          // so from end toward lastSource should match endPos exit direction.
          assertExitDirection(end, lastSource, endPos);
        },
      ),
      { numRuns: 100 },
    );
  });
});
