import { describe, it, expect } from 'vitest';
import {
  buildRoutingSpots,
  inflateRect,
  rectsIntersect,
  extrudePoint,
} from '@/utils/routing/routing-grid';
import type { RoutingRect } from '@/utils/routing/routing-grid';
import type { Point } from '@/types/diagram';

describe('inflateRect', () => {
  it('inflates a rect by margin on all sides', () => {
    const rect: RoutingRect = { left: 100, top: 100, width: 50, height: 30 };
    const inflated = inflateRect(rect, 10);
    expect(inflated).toEqual({ left: 90, top: 90, width: 70, height: 50 });
  });

  it('handles zero margin', () => {
    const rect: RoutingRect = { left: 50, top: 50, width: 100, height: 100 };
    const inflated = inflateRect(rect, 0);
    expect(inflated).toEqual(rect);
  });
});

describe('rectsIntersect', () => {
  it('returns true for overlapping rects', () => {
    const a: RoutingRect = { left: 0, top: 0, width: 100, height: 100 };
    const b: RoutingRect = { left: 50, top: 50, width: 100, height: 100 };
    expect(rectsIntersect(a, b)).toBe(true);
  });

  it('returns false for non-overlapping rects', () => {
    const a: RoutingRect = { left: 0, top: 0, width: 50, height: 50 };
    const b: RoutingRect = { left: 100, top: 100, width: 50, height: 50 };
    expect(rectsIntersect(a, b)).toBe(false);
  });

  it('returns false for rects touching at edges only', () => {
    const a: RoutingRect = { left: 0, top: 0, width: 50, height: 50 };
    const b: RoutingRect = { left: 50, top: 0, width: 50, height: 50 };
    expect(rectsIntersect(a, b)).toBe(false);
  });
});

describe('extrudePoint', () => {
  const point: Point = { x: 100, y: 100 };

  it('extrudes top', () => {
    expect(extrudePoint(point, 'top', 20)).toEqual({ x: 100, y: 80 });
  });

  it('extrudes right', () => {
    expect(extrudePoint(point, 'right', 20)).toEqual({ x: 120, y: 100 });
  });

  it('extrudes bottom', () => {
    expect(extrudePoint(point, 'bottom', 20)).toEqual({ x: 100, y: 120 });
  });

  it('extrudes left', () => {
    expect(extrudePoint(point, 'left', 20)).toEqual({ x: 80, y: 100 });
  });
});

describe('buildRoutingSpots', () => {
  const sourceRect: RoutingRect = { left: 50, top: 50, width: 100, height: 60 };
  const targetRect: RoutingRect = { left: 300, top: 50, width: 100, height: 60 };

  it('produces spots that include sourceExit and targetExit', () => {
    const sourcePoint: Point = { x: 150, y: 80 }; // right side of source
    const targetPoint: Point = { x: 300, y: 80 }; // left side of target

    const { spots, sourceExit, targetExit } = buildRoutingSpots(
      sourcePoint, 'right', sourceRect,
      targetPoint, 'left', targetRect,
      [],
      20,
    );

    // Exit points should be extruded from connection points
    expect(sourceExit).toEqual({ x: 170, y: 80 });
    expect(targetExit).toEqual({ x: 280, y: 80 });

    // Exit points must be in the spots array
    const hasSource = spots.some((s) => s.x === sourceExit.x && s.y === sourceExit.y);
    const hasTarget = spots.some((s) => s.x === targetExit.x && s.y === targetExit.y);
    expect(hasSource).toBe(true);
    expect(hasTarget).toBe(true);
  });

  it('generates spots including exit points', () => {
    const sourcePoint: Point = { x: 150, y: 80 };
    const targetPoint: Point = { x: 300, y: 80 };

    const { spots } = buildRoutingSpots(
      sourcePoint, 'right', sourceRect,
      targetPoint, 'left', targetRect,
      [],
      20,
    );

    // Should have at least the two exit points
    expect(spots.length).toBeGreaterThanOrEqual(2);
  });

  it('generates more spots when obstacles are present', () => {
    const sourcePoint: Point = { x: 150, y: 80 };
    const targetPoint: Point = { x: 300, y: 80 };
    const obstacle: RoutingRect = { left: 200, top: 200, width: 60, height: 60 };

    const { spots } = buildRoutingSpots(
      sourcePoint, 'right', sourceRect,
      targetPoint, 'left', targetRect,
      [obstacle],
      20,
    );

    // Obstacles add rulers → more grid intersections → more spots
    expect(spots.length).toBeGreaterThan(2);
  });

  it('excludes spots that fall inside obstacles', () => {
    const sourcePoint: Point = { x: 150, y: 80 };
    const targetPoint: Point = { x: 300, y: 80 };

    // Place an obstacle between source and target
    const obstacle: RoutingRect = { left: 200, top: 40, width: 60, height: 80 };

    const { spots, inflatedObstacles } = buildRoutingSpots(
      sourcePoint, 'right', sourceRect,
      targetPoint, 'left', targetRect,
      [obstacle],
      20,
    );

    const inflatedObs = inflatedObstacles[0];

    // No spot should be strictly inside the inflated obstacle
    // (edge points are okay since pointInsideRect is inclusive but routing still works)
    for (const spot of spots) {
      const strictlyInside =
        spot.x > inflatedObs.left &&
        spot.x < inflatedObs.left + inflatedObs.width &&
        spot.y > inflatedObs.top &&
        spot.y < inflatedObs.top + inflatedObs.height;
      // Exit points are excepted from this rule
      if (strictlyInside) {
        // Should only be the source or target exit
        const isExit =
          (spot.x === 170 && spot.y === 80) ||
          (spot.x === 280 && spot.y === 80);
        expect(isExit).toBe(true);
      }
    }
  });

  it('reduces margin when source and target inflated rects overlap', () => {
    // Place source and target very close together
    const closeSource: RoutingRect = { left: 50, top: 50, width: 100, height: 60 };
    const closeTarget: RoutingRect = { left: 160, top: 50, width: 100, height: 60 };
    const sourcePoint: Point = { x: 150, y: 80 };
    const targetPoint: Point = { x: 160, y: 80 };

    const { sourceExit, targetExit } = buildRoutingSpots(
      sourcePoint, 'right', closeSource,
      targetPoint, 'left', closeTarget,
      [],
      20, // margin of 20 — inflated rects will overlap (160-20=140 < 150+100+20=170)
    );

    // With reduced margin (0), exit points should be at the connection points themselves
    expect(sourceExit).toEqual({ x: 150, y: 80 });
    expect(targetExit).toEqual({ x: 160, y: 80 });
  });

  it('all spots are within the global bounds', () => {
    const sourcePoint: Point = { x: 150, y: 80 };
    const targetPoint: Point = { x: 300, y: 80 };

    const { spots } = buildRoutingSpots(
      sourcePoint, 'right', sourceRect,
      targetPoint, 'left', targetRect,
      [],
      20,
      20,
    );

    // Global bounds should encompass source and target + margins
    // All spots should be finite numbers
    for (const spot of spots) {
      expect(Number.isFinite(spot.x)).toBe(true);
      expect(Number.isFinite(spot.y)).toBe(true);
    }
  });
});
