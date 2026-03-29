import fc from 'fast-check';
import { computeOrthogonalWaypoints } from '@/utils/routing';
import type { Point } from '@/types/diagram';

// Feature: fixed-connection-routing
// **Property 5: Facing anchors on shared axis produce zero waypoints**
// **Validates: Requirements 2.3**

describe('Property 5: Facing anchors on shared axis produce zero waypoints', () => {
  test('source right / target left at same Y where target X > source X → empty waypoints', () => {
    fc.assert(
      fc.property(
        fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
        fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
        fc.double({ min: 1, max: 2000, noNaN: true, noDefaultInfinity: true }),
        (sourceX, sharedY, gap) => {
          const start: Point = { x: sourceX, y: sharedY };
          const end: Point = { x: sourceX + gap, y: sharedY };

          const waypoints = computeOrthogonalWaypoints(start, 'right', end, 'left');
          expect(waypoints).toEqual([]);
        },
      ),
      { numRuns: 100 },
    );
  });

  test('source left / target right at same Y where target X < source X → empty waypoints', () => {
    fc.assert(
      fc.property(
        fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
        fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
        fc.double({ min: 1, max: 2000, noNaN: true, noDefaultInfinity: true }),
        (sourceX, sharedY, gap) => {
          const start: Point = { x: sourceX, y: sharedY };
          const end: Point = { x: sourceX - gap, y: sharedY };

          const waypoints = computeOrthogonalWaypoints(start, 'left', end, 'right');
          expect(waypoints).toEqual([]);
        },
      ),
      { numRuns: 100 },
    );
  });

  test('source bottom / target top at same X where target Y > source Y → empty waypoints', () => {
    fc.assert(
      fc.property(
        fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
        fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
        fc.double({ min: 1, max: 2000, noNaN: true, noDefaultInfinity: true }),
        (sharedX, sourceY, gap) => {
          const start: Point = { x: sharedX, y: sourceY };
          const end: Point = { x: sharedX, y: sourceY + gap };

          const waypoints = computeOrthogonalWaypoints(start, 'bottom', end, 'top');
          expect(waypoints).toEqual([]);
        },
      ),
      { numRuns: 100 },
    );
  });

  test('source top / target bottom at same X where target Y < source Y → empty waypoints', () => {
    fc.assert(
      fc.property(
        fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
        fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
        fc.double({ min: 1, max: 2000, noNaN: true, noDefaultInfinity: true }),
        (sharedX, sourceY, gap) => {
          const start: Point = { x: sharedX, y: sourceY };
          const end: Point = { x: sharedX, y: sourceY - gap };

          const waypoints = computeOrthogonalWaypoints(start, 'top', end, 'bottom');
          expect(waypoints).toEqual([]);
        },
      ),
      { numRuns: 100 },
    );
  });
});
