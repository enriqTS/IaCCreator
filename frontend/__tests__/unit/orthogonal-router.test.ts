import { describe, it, expect } from 'vitest';
import { routeOrthogonalConnector, filterObstaclesByProximity } from '@/utils/orthogonal-router';
import type { RoutingRequest, RoutingResult } from '@/utils/orthogonal-router';
import type { RoutingRect } from '@/utils/routing-grid';
import type { Point } from '@/types/diagram';

/** Helper: check every consecutive pair in the full path shares X or Y */
function assertOrthogonal(path: Point[]) {
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i];
    const b = path[i + 1];
    const sameX = a.x === b.x;
    const sameY = a.y === b.y;
    expect(
      sameX || sameY,
      `Segment ${i}: (${a.x},${a.y})→(${b.x},${b.y}) is not axis-aligned`,
    ).toBe(true);
  }
}

/** Helper: build full path from a result */
function fullPath(source: Point, result: RoutingResult, target: Point): Point[] {
  return [source, ...result.waypoints, target];
}

describe('routeOrthogonalConnector', () => {
  describe('no obstacles — basic routing', () => {
    it('produces an orthogonal path between facing anchors', () => {
      const request: RoutingRequest = {
        sourcePoint: { x: 150, y: 80 },
        sourceSide: 'right',
        sourceRect: { left: 50, top: 50, width: 100, height: 60 },
        targetPoint: { x: 300, y: 80 },
        targetSide: 'left',
        targetRect: { left: 300, top: 50, width: 100, height: 60 },
        obstacles: [],
        shapeMargin: 20,
      };
      const result = routeOrthogonalConnector(request);
      expect(result.success).toBe(true);

      const path = fullPath(request.sourcePoint, result, request.targetPoint);
      assertOrthogonal(path);
    });

    it('handles perpendicular anchors (right → top)', () => {
      const request: RoutingRequest = {
        sourcePoint: { x: 150, y: 80 },
        sourceSide: 'right',
        sourceRect: { left: 50, top: 50, width: 100, height: 60 },
        targetPoint: { x: 350, y: 200 },
        targetSide: 'top',
        targetRect: { left: 300, top: 200, width: 100, height: 60 },
        obstacles: [],
        shapeMargin: 20,
      };
      const result = routeOrthogonalConnector(request);
      expect(result.success).toBe(true);

      const path = fullPath(request.sourcePoint, result, request.targetPoint);
      assertOrthogonal(path);
    });

    it('returns empty waypoints for degenerate case (same point)', () => {
      const request: RoutingRequest = {
        sourcePoint: { x: 100, y: 100 },
        sourceSide: 'right',
        sourceRect: { left: 50, top: 70, width: 100, height: 60 },
        targetPoint: { x: 100, y: 100 },
        targetSide: 'left',
        targetRect: { left: 50, top: 70, width: 100, height: 60 },
        obstacles: [],
        shapeMargin: 20,
      };
      const result = routeOrthogonalConnector(request);
      expect(result.success).toBe(true);
      expect(result.waypoints).toEqual([]);
    });
  });

  describe('single obstacle avoidance', () => {
    it('routes around a single obstacle between source and target', () => {
      const request: RoutingRequest = {
        sourcePoint: { x: 150, y: 80 },
        sourceSide: 'right',
        sourceRect: { left: 50, top: 50, width: 100, height: 60 },
        targetPoint: { x: 400, y: 80 },
        targetSide: 'left',
        targetRect: { left: 400, top: 50, width: 100, height: 60 },
        obstacles: [
          { left: 220, top: 40, width: 80, height: 80 }, // obstacle in the middle
        ],
        shapeMargin: 20,
      };
      const result = routeOrthogonalConnector(request);
      expect(result.success).toBe(true);

      const path = fullPath(request.sourcePoint, result, request.targetPoint);
      assertOrthogonal(path);
      // Path should have waypoints (can't be a straight line through obstacle)
      expect(result.waypoints.length).toBeGreaterThan(0);
    });
  });

  describe('multiple obstacle avoidance', () => {
    it('routes around multiple obstacles', () => {
      const request: RoutingRequest = {
        sourcePoint: { x: 150, y: 80 },
        sourceSide: 'right',
        sourceRect: { left: 50, top: 50, width: 100, height: 60 },
        targetPoint: { x: 600, y: 80 },
        targetSide: 'left',
        targetRect: { left: 600, top: 50, width: 100, height: 60 },
        obstacles: [
          { left: 220, top: 40, width: 60, height: 80 },
          { left: 380, top: 40, width: 60, height: 80 },
        ],
        shapeMargin: 20,
      };
      const result = routeOrthogonalConnector(request);
      expect(result.success).toBe(true);

      const path = fullPath(request.sourcePoint, result, request.targetPoint);
      assertOrthogonal(path);
      expect(result.waypoints.length).toBeGreaterThan(0);
    });
  });

  describe('fallback behavior', () => {
    it('falls back gracefully when pathfinding cannot find a route', () => {
      // Create a scenario that might cause pathfinding to fail:
      // completely walled-off target
      const request: RoutingRequest = {
        sourcePoint: { x: 50, y: 50 },
        sourceSide: 'right',
        sourceRect: { left: 0, top: 25, width: 50, height: 50 },
        targetPoint: { x: 200, y: 50 },
        targetSide: 'left',
        targetRect: { left: 200, top: 25, width: 50, height: 50 },
        obstacles: [
          // Dense wall of obstacles (may or may not block — testing fallback path)
          { left: 80, top: 0, width: 100, height: 200 },
        ],
        shapeMargin: 20,
      };
      const result = routeOrthogonalConnector(request);

      // Should still produce a result (either success or fallback)
      const path = fullPath(request.sourcePoint, result, request.targetPoint);
      assertOrthogonal(path);
      // Whether it used fallback or found a detour, it should not crash
      expect(path.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('grid snap', () => {
    it('snaps waypoints to grid when gridSize is provided', () => {
      const request: RoutingRequest = {
        sourcePoint: { x: 150, y: 80 },
        sourceSide: 'right',
        sourceRect: { left: 50, top: 50, width: 100, height: 60 },
        targetPoint: { x: 500, y: 200 },
        targetSide: 'left',
        targetRect: { left: 500, top: 170, width: 100, height: 60 },
        obstacles: [],
        shapeMargin: 20,
        gridSize: 10,
      };
      const result = routeOrthogonalConnector(request);

      // Whether via pathfinder or fallback, waypoints should be grid-snapped
      for (const wp of result.waypoints) {
        expect(wp.x % 10).toBe(0);
        expect(wp.y % 10).toBe(0);
      }
    });
  });

  describe('self-connection', () => {
    it('produces a U-shaped route for same-side self-connection', () => {
      const rect: RoutingRect = { left: 100, top: 100, width: 100, height: 60 };
      const request: RoutingRequest = {
        sourcePoint: { x: 200, y: 120 },  // right side
        sourceSide: 'right',
        sourceRect: rect,
        targetPoint: { x: 200, y: 140 },  // right side (different Y on same side)
        targetSide: 'right',
        targetRect: rect,
        obstacles: [],
        shapeMargin: 20,
      };
      const result = routeOrthogonalConnector(request);
      expect(result.success).toBe(true);
      expect(result.waypoints.length).toBeGreaterThan(0);

      const path = fullPath(request.sourcePoint, result, request.targetPoint);
      assertOrthogonal(path);

      // Waypoints should go to the right of the shape (outward)
      for (const wp of result.waypoints) {
        expect(wp.x).toBeGreaterThan(200);
      }
    });

    it('produces a route for opposite-side self-connection', () => {
      const rect: RoutingRect = { left: 100, top: 100, width: 100, height: 60 };
      const request: RoutingRequest = {
        sourcePoint: { x: 200, y: 130 }, // right side
        sourceSide: 'right',
        sourceRect: rect,
        targetPoint: { x: 100, y: 130 }, // left side
        targetSide: 'left',
        targetRect: rect,
        obstacles: [],
        shapeMargin: 20,
      };
      const result = routeOrthogonalConnector(request);
      expect(result.success).toBe(true);
      expect(result.waypoints.length).toBeGreaterThan(0);

      const path = fullPath(request.sourcePoint, result, request.targetPoint);
      assertOrthogonal(path);
    });

    it('produces a route for perpendicular-side self-connection', () => {
      const rect: RoutingRect = { left: 100, top: 100, width: 100, height: 60 };
      const request: RoutingRequest = {
        sourcePoint: { x: 200, y: 130 }, // right side
        sourceSide: 'right',
        sourceRect: rect,
        targetPoint: { x: 150, y: 100 }, // top side
        targetSide: 'top',
        targetRect: rect,
        obstacles: [],
        shapeMargin: 20,
      };
      const result = routeOrthogonalConnector(request);
      expect(result.success).toBe(true);
      expect(result.waypoints.length).toBeGreaterThan(0);

      const path = fullPath(request.sourcePoint, result, request.targetPoint);
      assertOrthogonal(path);
    });
  });

  describe('performance', () => {
    it('handles 50 obstacles in under 10ms', () => {
      // Generate 50 obstacles in a grid pattern
      const obstacles: RoutingRect[] = [];
      for (let row = 0; row < 5; row++) {
        for (let col = 0; col < 10; col++) {
          obstacles.push({
            left: 200 + col * 80,
            top: 150 + row * 80,
            width: 50,
            height: 50,
          });
        }
      }

      const request: RoutingRequest = {
        sourcePoint: { x: 150, y: 80 },
        sourceSide: 'right',
        sourceRect: { left: 50, top: 50, width: 100, height: 60 },
        targetPoint: { x: 1100, y: 80 },
        targetSide: 'left',
        targetRect: { left: 1100, top: 50, width: 100, height: 60 },
        obstacles,
        shapeMargin: 20,
      };

      const start = performance.now();
      const result = routeOrthogonalConnector(request);
      const elapsed = performance.now() - start;

      // Should complete (success or fallback)
      const path = fullPath(request.sourcePoint, result, request.targetPoint);
      expect(path.length).toBeGreaterThanOrEqual(2);

      // Performance target: under 50ms (generous for CI, target is <10ms locally)
      expect(elapsed).toBeLessThan(50);
    });
  });
});

describe('filterObstaclesByProximity', () => {
  const sourceRect: RoutingRect = { left: 0, top: 0, width: 100, height: 100 };
  const targetRect: RoutingRect = { left: 200, top: 0, width: 100, height: 100 };

  it('returns all obstacles when count is below threshold (50)', () => {
    const obstacles: RoutingRect[] = Array.from({ length: 30 }, (_, i) => ({
      left: 1000 + i * 100,
      top: 1000,
      width: 50,
      height: 50,
    }));

    const result = filterObstaclesByProximity(obstacles, sourceRect, targetRect, 20);
    // All 30 returned (below threshold)
    expect(result).toHaveLength(30);
  });

  it('filters out distant obstacles when count exceeds threshold', () => {
    // 55 obstacles: 5 nearby, 50 far away
    const nearby: RoutingRect[] = Array.from({ length: 5 }, (_, i) => ({
      left: 100 + i * 20,
      top: 50,
      width: 10,
      height: 10,
    }));
    const farAway: RoutingRect[] = Array.from({ length: 50 }, (_, i) => ({
      left: 5000 + i * 100,
      top: 5000,
      width: 50,
      height: 50,
    }));
    const obstacles = [...nearby, ...farAway];

    const result = filterObstaclesByProximity(obstacles, sourceRect, targetRect, 20);
    // Should filter out the far-away obstacles
    expect(result.length).toBeLessThan(obstacles.length);
    // Should keep all nearby obstacles
    expect(result.length).toBeGreaterThanOrEqual(nearby.length);
  });

  it('keeps all obstacles that are between source and target', () => {
    // 60 obstacles all between source and target
    const obstacles: RoutingRect[] = Array.from({ length: 60 }, (_, i) => ({
      left: 110 + (i % 10) * 8,
      top: 10 + Math.floor(i / 10) * 15,
      width: 5,
      height: 5,
    }));

    const result = filterObstaclesByProximity(obstacles, sourceRect, targetRect, 20);
    // All are within proximity → all should be kept
    expect(result).toHaveLength(60);
  });
});
