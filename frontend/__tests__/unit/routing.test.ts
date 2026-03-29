import { describe, it, expect } from 'vitest';
import { computeOrthogonalWaypoints, MIN_OFFSET } from '@/utils/routing';
import type { Point } from '@/types/diagram';
import type { AnchorPosition } from '@/utils/anchor';

/** Helper: build full path including start and end */
function fullPath(start: Point, waypoints: Point[], end: Point): Point[] {
  return [start, ...waypoints, end];
}

/** Helper: check every consecutive pair shares X or Y */
function assertOrthogonal(path: Point[]) {
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i];
    const b = path[i + 1];
    const sameX = a.x === b.x;
    const sameY = a.y === b.y;
    expect(sameX || sameY, `Segment ${i}: (${a.x},${a.y})→(${b.x},${b.y}) is not axis-aligned`).toBe(true);
  }
}

describe('computeOrthogonalWaypoints', () => {
  describe('degenerate case', () => {
    it('returns empty array when start === end', () => {
      const p: Point = { x: 100, y: 200 };
      const result = computeOrthogonalWaypoints(p, 'right', p, 'left');
      expect(result).toEqual([]);
    });
  });

  describe('Case 1: Facing anchors, aligned — zero waypoints', () => {
    it('source right → target left at same Y', () => {
      const start: Point = { x: 100, y: 200 };
      const end: Point = { x: 300, y: 200 };
      const result = computeOrthogonalWaypoints(start, 'right', end, 'left');
      expect(result).toEqual([]);
    });

    it('source left → target right at same Y', () => {
      const start: Point = { x: 300, y: 200 };
      const end: Point = { x: 100, y: 200 };
      const result = computeOrthogonalWaypoints(start, 'left', end, 'right');
      expect(result).toEqual([]);
    });

    it('source bottom → target top at same X', () => {
      const start: Point = { x: 200, y: 100 };
      const end: Point = { x: 200, y: 300 };
      const result = computeOrthogonalWaypoints(start, 'bottom', end, 'top');
      expect(result).toEqual([]);
    });

    it('source top → target bottom at same X', () => {
      const start: Point = { x: 200, y: 300 };
      const end: Point = { x: 200, y: 100 };
      const result = computeOrthogonalWaypoints(start, 'top', end, 'bottom');
      expect(result).toEqual([]);
    });
  });

  describe('Case 2: Facing anchors, offset — two waypoints S-shape', () => {
    it('source right → target left, different Y', () => {
      const start: Point = { x: 100, y: 100 };
      const end: Point = { x: 300, y: 200 };
      const result = computeOrthogonalWaypoints(start, 'right', end, 'left');
      expect(result).toHaveLength(2);
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
      // First waypoint at start's Y
      expect(result[0].y).toBe(start.y);
      // Second waypoint at end's Y
      expect(result[1].y).toBe(end.y);
      // Both at same X (the midpoint)
      expect(result[0].x).toBe(result[1].x);
    });

    it('source bottom → target top, different X', () => {
      const start: Point = { x: 100, y: 100 };
      const end: Point = { x: 200, y: 300 };
      const result = computeOrthogonalWaypoints(start, 'bottom', end, 'top');
      expect(result).toHaveLength(2);
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
      expect(result[0].x).toBe(start.x);
      expect(result[1].x).toBe(end.x);
      expect(result[0].y).toBe(result[1].y);
    });
  });

  describe('Case 3: Perpendicular anchors — one waypoint at corner', () => {
    it('source right → target top, corner satisfies offset', () => {
      const start: Point = { x: 100, y: 100 };
      const end: Point = { x: 300, y: 300 };
      const result = computeOrthogonalWaypoints(start, 'right', end, 'top');
      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({ x: 300, y: 100 });
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
    });

    it('source bottom → target left, corner satisfies offset', () => {
      // Corner at (start.x, end.y) = (100, 300)
      // startOk: 1*(300-100)=200 >= 20 ✓, endOk: -1*(100-300)=200 >= 20 ✓
      const start: Point = { x: 100, y: 100 };
      const end: Point = { x: 300, y: 300 };
      const result = computeOrthogonalWaypoints(start, 'bottom', end, 'left');
      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({ x: 100, y: 300 });
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
    });

    it('source bottom → target right, corner does NOT satisfy — 3 waypoints', () => {
      // Corner at (100, 300), endDir.x=1, corner.x-end.x = 100-300 = -200 < 20
      const start: Point = { x: 100, y: 100 };
      const end: Point = { x: 300, y: 300 };
      const result = computeOrthogonalWaypoints(start, 'bottom', end, 'right');
      expect(result).toHaveLength(3);
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
    });

    it('source right → target bottom, corner does NOT satisfy offset — 3 waypoints', () => {
      const start: Point = { x: 100, y: 100 };
      const end: Point = { x: 110, y: 105 };
      const result = computeOrthogonalWaypoints(start, 'right', end, 'bottom');
      expect(result).toHaveLength(3);
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
    });
  });

  describe('Case 4: Same-side anchors — U-shape with 2 waypoints', () => {
    it('source right → target right', () => {
      const start: Point = { x: 100, y: 100 };
      const end: Point = { x: 200, y: 200 };
      const result = computeOrthogonalWaypoints(start, 'right', end, 'right');
      expect(result).toHaveLength(2);
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
      // The U-shape should extend to the right of both
      const maxExitX = Math.max(start.x + MIN_OFFSET, end.x + MIN_OFFSET);
      expect(result[0].x).toBe(maxExitX);
      expect(result[1].x).toBe(maxExitX);
    });

    it('source left → target left', () => {
      const start: Point = { x: 200, y: 100 };
      const end: Point = { x: 100, y: 200 };
      const result = computeOrthogonalWaypoints(start, 'left', end, 'left');
      expect(result).toHaveLength(2);
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
      const minExitX = Math.min(start.x - MIN_OFFSET, end.x - MIN_OFFSET);
      expect(result[0].x).toBe(minExitX);
      expect(result[1].x).toBe(minExitX);
    });

    it('source top → target top', () => {
      const start: Point = { x: 100, y: 200 };
      const end: Point = { x: 200, y: 100 };
      const result = computeOrthogonalWaypoints(start, 'top', end, 'top');
      expect(result).toHaveLength(2);
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
      const minExitY = Math.min(start.y - MIN_OFFSET, end.y - MIN_OFFSET);
      expect(result[0].y).toBe(minExitY);
      expect(result[1].y).toBe(minExitY);
    });

    it('source bottom → target bottom', () => {
      const start: Point = { x: 100, y: 100 };
      const end: Point = { x: 200, y: 200 };
      const result = computeOrthogonalWaypoints(start, 'bottom', end, 'bottom');
      expect(result).toHaveLength(2);
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
      const maxExitY = Math.max(start.y + MIN_OFFSET, end.y + MIN_OFFSET);
      expect(result[0].y).toBe(maxExitY);
      expect(result[1].y).toBe(maxExitY);
    });
  });

  describe('Case 5: Opposing anchors, wrong direction — detour waypoints', () => {
    it('source right → target left, target is to the LEFT', () => {
      const start: Point = { x: 300, y: 100 };
      const end: Point = { x: 100, y: 200 };
      const result = computeOrthogonalWaypoints(start, 'right', end, 'left');
      expect(result.length).toBeGreaterThanOrEqual(3);
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
      // First waypoint exits right from start
      expect(result[0].x).toBe(start.x + MIN_OFFSET);
      expect(result[0].y).toBe(start.y);
    });

    it('source bottom → target top, target is ABOVE', () => {
      const start: Point = { x: 100, y: 300 };
      const end: Point = { x: 200, y: 100 };
      const result = computeOrthogonalWaypoints(start, 'bottom', end, 'top');
      expect(result.length).toBeGreaterThanOrEqual(3);
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
      // First waypoint exits downward from start
      expect(result[0].x).toBe(start.x);
      expect(result[0].y).toBe(start.y + MIN_OFFSET);
    });
  });

  describe('MIN_OFFSET constant', () => {
    it('exports MIN_OFFSET = 20', () => {
      expect(MIN_OFFSET).toBe(20);
    });
  });

  describe('custom minOffset', () => {
    it('respects custom minOffset value', () => {
      const start: Point = { x: 100, y: 100 };
      const end: Point = { x: 100, y: 200 };
      const customOffset = 50;
      const result = computeOrthogonalWaypoints(start, 'right', end, 'right', customOffset);
      expect(result).toHaveLength(2);
      const path = fullPath(start, result, end);
      assertOrthogonal(path);
      // U-shape should extend by customOffset
      expect(result[0].x).toBe(start.x + customOffset);
    });
  });

  describe('all paths are orthogonal', () => {
    const positions: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];
    const testPoints: Point[] = [
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      { x: 0, y: 100 },
      { x: 100, y: 100 },
      { x: 50, y: 200 },
      { x: -50, y: -50 },
    ];

    for (const sp of positions) {
      for (const ep of positions) {
        for (const start of testPoints) {
          for (const end of testPoints) {
            if (start.x === end.x && start.y === end.y) continue;
            it(`${sp}→${ep} from (${start.x},${start.y}) to (${end.x},${end.y})`, () => {
              const waypoints = computeOrthogonalWaypoints(start, sp, end, ep);
              const path = fullPath(start, waypoints, end);
              assertOrthogonal(path);
            });
          }
        }
      }
    }
  });
});
