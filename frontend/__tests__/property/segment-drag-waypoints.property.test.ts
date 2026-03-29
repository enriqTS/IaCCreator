/**
 * Property-based test: Segment drag updates waypoints to reflect new position
 *
 * Feature: line-segment-manipulation, Property 5: Segment drag updates waypoints to reflect new position
 *
 * **Validates: Requirements 3.4, 3.6**
 *
 * For any orthogonal line with at least one draggable segment, and any valid drag delta,
 * the resulting waypoints contain the segment at the new position (original position + delta
 * along the constrained axis), and the path remains composed of only horizontal and vertical segments.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import type { Point } from '@/types/diagram';
import {
  computeDraggableSegments,
  computeNewWaypoints,
} from '@/components/canvas/SegmentHandles';

/**
 * Generator for orthogonal paths with at least 4 points.
 * Builds a path starting from a random origin, alternating between
 * horizontal and vertical segments.
 */
const orthogonalPathArb: fc.Arbitrary<Point[]> = fc
  .record({
    startX: fc.integer({ min: -2000, max: 2000 }),
    startY: fc.integer({ min: -2000, max: 2000 }),
    deltas: fc.array(fc.integer({ min: -500, max: 500 }).filter((d) => d !== 0), {
      minLength: 3,
      maxLength: 8,
    }),
    startHorizontal: fc.boolean(),
  })
  .map(({ startX, startY, deltas, startHorizontal }) => {
    const points: Point[] = [{ x: startX, y: startY }];
    let x = startX;
    let y = startY;
    for (let i = 0; i < deltas.length; i++) {
      const isHorizontal = startHorizontal ? i % 2 === 0 : i % 2 !== 0;
      if (isHorizontal) {
        x += deltas[i];
      } else {
        y += deltas[i];
      }
      points.push({ x, y });
    }
    return points;
  });

/** Arbitrary for a drag delta. */
const deltaArb = fc.integer({ min: -500, max: 500 }).filter((d) => d !== 0);

/**
 * Check that every consecutive pair of points in a path forms either
 * a horizontal segment (same y) or a vertical segment (same x).
 */
function isOrthogonalPath(points: Point[]): boolean {
  for (let i = 0; i < points.length - 1; i++) {
    const p1 = points[i];
    const p2 = points[i + 1];
    if (p1.x !== p2.x && p1.y !== p2.y) {
      return false;
    }
  }
  return true;
}

describe('Feature: line-segment-manipulation, Property 5: Segment drag updates waypoints to reflect new position', () => {
  it('dragged segment appears at the new position in the resulting waypoints', () => {
    /**
     * **Validates: Requirements 3.4, 3.6**
     *
     * Strategy: Generate random orthogonal paths and deltas. Pick a draggable segment,
     * apply computeNewWaypoints with the delta. Reconstruct the full path and verify
     * the dragged segment's coordinate has shifted by exactly delta along the constrained axis.
     */
    fc.assert(
      fc.property(orthogonalPathArb, deltaArb, (path, delta) => {
        const segments = computeDraggableSegments(path);
        if (segments.length === 0) return; // skip paths with no draggable segments

        // Pick the first draggable segment for testing
        const seg = segments[0];
        const newWaypoints = computeNewWaypoints(path, seg.index, seg.orientation, delta);

        // Reconstruct full path: start + waypoints + end
        const fullPath = [path[0], ...newWaypoints, path[path.length - 1]];

        // The dragged segment's two points in the original path
        const origP1 = path[seg.index];
        const origP2 = path[seg.index + 1];

        if (seg.orientation === 'horizontal') {
          // Horizontal segment dragged vertically: new y = original y + delta
          const expectedY = origP1.y + delta;
          // Find a point in the new waypoints that has the expected y and matching x values
          // The waypoints are path[1..n-2], so the segment index in waypoints is seg.index - 1
          const wpIdx = seg.index - 1;
          // After collapse, the waypoint might have been merged, but the segment should still exist
          // if the delta is non-zero and doesn't create a zero-length segment with neighbors
          // Check that the full path contains the expected segment position
          const hasExpectedSegment = fullPath.some((p, i) => {
            if (i >= fullPath.length - 1) return false;
            const next = fullPath[i + 1];
            return p.y === expectedY && next.y === expectedY &&
                   ((p.x === origP1.x && next.x === origP2.x) ||
                    (p.x === origP2.x && next.x === origP1.x));
          });
          expect(hasExpectedSegment).toBe(true);
        } else {
          // Vertical segment dragged horizontally: new x = original x + delta
          const expectedX = origP1.x + delta;
          const hasExpectedSegment = fullPath.some((p, i) => {
            if (i >= fullPath.length - 1) return false;
            const next = fullPath[i + 1];
            return p.x === expectedX && next.x === expectedX &&
                   ((p.y === origP1.y && next.y === origP2.y) ||
                    (p.y === origP2.y && next.y === origP1.y));
          });
          expect(hasExpectedSegment).toBe(true);
        }
      }),
      { numRuns: 100 },
    );
  });

  it('the full path remains orthogonal after a segment drag', () => {
    /**
     * **Validates: Requirements 3.4, 3.6**
     *
     * Strategy: Generate random orthogonal paths and deltas. Apply computeNewWaypoints.
     * Reconstruct the full path [start, ...waypoints, end] and verify every consecutive
     * pair of points forms either a horizontal or vertical segment.
     */
    fc.assert(
      fc.property(orthogonalPathArb, deltaArb, (path, delta) => {
        const segments = computeDraggableSegments(path);
        if (segments.length === 0) return;

        const seg = segments[0];
        const newWaypoints = computeNewWaypoints(path, seg.index, seg.orientation, delta);
        const fullPath = [path[0], ...newWaypoints, path[path.length - 1]];

        expect(isOrthogonalPath(fullPath)).toBe(true);
      }),
      { numRuns: 100 },
    );
  });
});
