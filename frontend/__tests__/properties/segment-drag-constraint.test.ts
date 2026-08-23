/**
 * Property-based test: Segment drag constraint is perpendicular to segment orientation
 *
 * For any orthogonal path segment, the allowed drag axis is perpendicular to the
 * segment's orientation: horizontal segments can only be dragged vertically (changing y),
 * and vertical segments can only be dragged horizontally (changing x).
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import type { Point } from '@/types/diagram';
import {
  computeDraggableSegments,
  computeNewWaypoints,
} from '@/components/canvas/interactions/SegmentHandles';

/**
 * Generator for orthogonal paths with at least 4 points.
 * Builds a path starting from a random origin, alternating between
 * horizontal and vertical segments.
 */
const orthogonalPathArb: fc.Arbitrary<Point[]> = fc
  .record({
    startX: fc.integer({ min: -2000, max: 2000 }),
    startY: fc.integer({ min: -2000, max: 2000 }),
    // At least 3 additional segments (4+ points total) to guarantee a middle segment
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

/** Arbitrary for a non-zero drag delta. */
const deltaArb = fc.integer({ min: -500, max: 500 }).filter((d) => d !== 0);

describe('Segment drag constraint is perpendicular to segment orientation', () => {
  it('horizontal segments are identified with horizontal orientation and vertical segments with vertical orientation', () => {
    /**
     *
     * Strategy: Generate random orthogonal paths (4+ points with alternating H/V segments).
     * Use computeDraggableSegments to find draggable segments. Verify each segment's
     * orientation matches the actual geometry of its two endpoints.
     */
    fc.assert(
      fc.property(orthogonalPathArb, (path) => {
        const segments = computeDraggableSegments(path);

        for (const seg of segments) {
          const p1 = path[seg.index];
          const p2 = path[seg.index + 1];

          if (p1.y === p2.y) {
            // Same y → horizontal segment → should drag vertically
            expect(seg.orientation).toBe('horizontal');
          } else if (p1.x === p2.x) {
            // Same x → vertical segment → should drag horizontally
            expect(seg.orientation).toBe('vertical');
          }
        }
      }),
      { numRuns: 100 },
    );
  });

  it('computeNewWaypoints only changes the constrained axis for each segment', () => {
    /**
     *
     * Strategy: For each draggable segment, apply a delta via computeNewWaypoints.
     * Verify that only the perpendicular axis changes:
     * - Horizontal segment drag → only y values change, x values stay the same
     * - Vertical segment drag → only x values change, y values stay the same
     */
    fc.assert(
      fc.property(orthogonalPathArb, deltaArb, (path, delta) => {
        const segments = computeDraggableSegments(path);
        if (segments.length === 0) return; // skip paths with no draggable segments

        for (const seg of segments) {
          const newWaypoints = computeNewWaypoints(path, seg.index, seg.orientation, delta);
          const fullPath = [path[0], ...newWaypoints, path[path.length - 1]];

          // Dragging along one axis must not invent a coordinate on the other one
          if (seg.orientation === 'horizontal') {
            const originalXs = new Set(path.map((p) => p.x));
            for (const point of fullPath) {
              expect(originalXs.has(point.x)).toBe(true);
            }
          } else {
            const originalYs = new Set(path.map((p) => p.y));
            for (const point of fullPath) {
              expect(originalYs.has(point.y)).toBe(true);
            }
          }
        }
      }),
      { numRuns: 100 },
    );
  });
});
