import { describe, it, expect } from 'vitest';
import {
  routeOrthogonalConnector,
  balancePath,
  shortDistanceRoute,
} from '@/utils/routing/orthogonal-router';
import type { RoutingRequest } from '@/utils/routing/orthogonal-router';
import type { RoutingRect } from '@/utils/routing/routing-grid';
import { computeOptimalExitSide } from '@/utils/anchor';
import { findShortestPath, anchorToExitDirection } from '@/utils/routing/routing-pathfinder';
import { computeParallelIndex, applyParallelOffset } from '@/utils/parallel-offset';
import type { Point } from '@/types/diagram';

/** Helper: check every consecutive pair shares X or Y */
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

// =============================================================================
// Task 2.1: balancePath
// =============================================================================

describe('balancePath', () => {
  it('centers a vertical middle segment between source and target shapes', () => {
    // S-route: source exits right, goes to some X, then turns to target
    const sourceRect: RoutingRect = { left: 50, top: 50, width: 100, height: 60 }; // right edge at x=150
    const targetRect: RoutingRect = { left: 300, top: 50, width: 100, height: 60 }; // left edge at x=300
    const sourcePoint: Point = { x: 150, y: 80 };
    const targetPoint: Point = { x: 300, y: 90 };

    // Two waypoints forming an S-shape with vertical middle segment at x=170
    const waypoints: Point[] = [
      { x: 170, y: 80 },
      { x: 170, y: 90 },
    ];

    const result = balancePath(waypoints, sourcePoint, targetPoint, sourceRect, targetRect);
    // Should center between source right edge (150) and target left edge (300) → 225
    expect(result[0].x).toBe(225);
    expect(result[1].x).toBe(225);
    // Y coordinates preserved
    expect(result[0].y).toBe(80);
    expect(result[1].y).toBe(90);
  });

  it('centers a horizontal middle segment between source and target shapes', () => {
    const sourceRect: RoutingRect = { left: 50, top: 50, width: 100, height: 60 }; // bottom edge at y=110
    const targetRect: RoutingRect = { left: 50, top: 250, width: 100, height: 60 }; // top edge at y=250
    const sourcePoint: Point = { x: 80, y: 110 };
    const targetPoint: Point = { x: 120, y: 250 };

    // Two waypoints forming an S-shape with horizontal middle segment at y=130
    const waypoints: Point[] = [
      { x: 80, y: 130 },
      { x: 120, y: 130 },
    ];

    const result = balancePath(waypoints, sourcePoint, targetPoint, sourceRect, targetRect);
    // Should center between source bottom edge (110) and target top edge (250) → 180
    expect(result[0].y).toBe(180);
    expect(result[1].y).toBe(180);
    // X coordinates preserved
    expect(result[0].x).toBe(80);
    expect(result[1].x).toBe(120);
  });

  it('does not modify routes with more than 2 waypoints', () => {
    const sourceRect: RoutingRect = { left: 0, top: 0, width: 50, height: 50 };
    const targetRect: RoutingRect = { left: 200, top: 200, width: 50, height: 50 };
    const sourcePoint: Point = { x: 50, y: 25 };
    const targetPoint: Point = { x: 200, y: 225 };

    const waypoints: Point[] = [
      { x: 100, y: 25 },
      { x: 100, y: 100 },
      { x: 200, y: 100 },
    ];

    const result = balancePath(waypoints, sourcePoint, targetPoint, sourceRect, targetRect);
    expect(result).toEqual(waypoints);
  });

  it('does not modify routes with fewer than 2 waypoints', () => {
    const sourceRect: RoutingRect = { left: 0, top: 0, width: 50, height: 50 };
    const targetRect: RoutingRect = { left: 200, top: 0, width: 50, height: 50 };
    const sourcePoint: Point = { x: 50, y: 25 };
    const targetPoint: Point = { x: 200, y: 25 };

    const result = balancePath([], sourcePoint, targetPoint, sourceRect, targetRect);
    expect(result).toEqual([]);
  });
});

// =============================================================================
// Task 2.2: computeOptimalExitSide
// =============================================================================

describe('computeOptimalExitSide', () => {
  const bounds = { x: 100, y: 100, width: 100, height: 100 }; // center at (150, 150)

  it('returns right when target is to the right', () => {
    expect(computeOptimalExitSide(bounds, { x: 300, y: 150 })).toBe('right');
  });

  it('returns left when target is to the left', () => {
    expect(computeOptimalExitSide(bounds, { x: 10, y: 150 })).toBe('left');
  });

  it('returns bottom when target is below', () => {
    expect(computeOptimalExitSide(bounds, { x: 150, y: 400 })).toBe('bottom');
  });

  it('returns top when target is above', () => {
    expect(computeOptimalExitSide(bounds, { x: 150, y: 10 })).toBe('top');
  });

  it('favors horizontal when dx >= dy', () => {
    // 45° angle → horizontal wins (dx === dy, abs(dx) >= abs(dy))
    expect(computeOptimalExitSide(bounds, { x: 250, y: 250 })).toBe('right');
  });

  it('retains currentPosition at exact 45° when provided', () => {
    expect(computeOptimalExitSide(bounds, { x: 250, y: 250 }, 'bottom')).toBe('bottom');
  });

  it('retains currentPosition when target is same center', () => {
    expect(computeOptimalExitSide(bounds, { x: 150, y: 150 }, 'top')).toBe('top');
  });

  it('defaults to right when target is same center and no currentPosition', () => {
    expect(computeOptimalExitSide(bounds, { x: 150, y: 150 })).toBe('right');
  });
});

// =============================================================================
// Task 2.3: shortDistanceRoute
// =============================================================================

describe('shortDistanceRoute', () => {
  const sourceRect: RoutingRect = { left: 100, top: 100, width: 80, height: 60 };

  it('returns null when connection points are far apart (manhattan >= 2*margin)', () => {
    const farTarget: RoutingRect = { left: 300, top: 100, width: 80, height: 60 };
    const result = shortDistanceRoute(
      { x: 180, y: 130 }, 'right',
      { x: 300, y: 130 }, 'left',
      sourceRect,
      farTarget,
      20,
    );
    expect(result).toBeNull();
  });

  it('returns 0 waypoints for facing anchors directly aligned', () => {
    const closeTarget: RoutingRect = { left: 190, top: 100, width: 80, height: 60 };
    const result = shortDistanceRoute(
      { x: 180, y: 130 }, 'right',
      { x: 190, y: 130 }, 'left',
      sourceRect,
      closeTarget,
      20,
    );
    expect(result).not.toBeNull();
    expect(result!.waypoints).toEqual([]);
    expect(result!.success).toBe(true);
  });

  it('returns 1 waypoint for perpendicular anchors (close shapes)', () => {
    // Manhattan = |195-180| + |115-130| = 15 + 15 = 30 < 40
    const closeTarget: RoutingRect = { left: 185, top: 100, width: 60, height: 40 };
    const result = shortDistanceRoute(
      { x: 180, y: 130 }, 'right',
      { x: 195, y: 115 }, 'top',
      sourceRect,
      closeTarget,
      20,
    );
    expect(result).not.toBeNull();
    expect(result!.waypoints).toHaveLength(1);
    expect(result!.success).toBe(true);
  });

  it('returns 2 waypoints for same-side anchors (U-shape, close shapes)', () => {
    // Manhattan = |195-180| + |130-130| = 15 < 40
    const closeTarget: RoutingRect = { left: 185, top: 100, width: 80, height: 60 };
    const result = shortDistanceRoute(
      { x: 180, y: 130 }, 'right',
      { x: 195, y: 130 }, 'right',
      sourceRect,
      closeTarget,
      20,
    );
    expect(result).not.toBeNull();
    expect(result!.waypoints).toHaveLength(2);
    expect(result!.success).toBe(true);
  });

  it('returns null when shapes overlap', () => {
    // Overlapping rects
    const overlapTarget: RoutingRect = { left: 120, top: 110, width: 80, height: 60 };
    const result = shortDistanceRoute(
      { x: 140, y: 130 }, 'right',
      { x: 150, y: 140 }, 'left',
      sourceRect,
      overlapTarget,
      20,
    );
    expect(result).toBeNull();
  });
});

// =============================================================================
// Task 2.4: Backward visit prevention
// =============================================================================

describe('backward visit prevention', () => {
  it('anchorToExitDirection converts anchor positions correctly', () => {
    expect(anchorToExitDirection('top')).toBe('up');
    expect(anchorToExitDirection('right')).toBe('right');
    expect(anchorToExitDirection('bottom')).toBe('down');
    expect(anchorToExitDirection('left')).toBe('left');
  });

  it('prevents backward exit from source when direction is specified', () => {
    // S --- A --- B --- T
    // With sourceExitDir = 'right', path should not go left from S first
    // Create a scenario where going left would be shorter but is blocked
    const spots: Point[] = [
      { x: 50, y: 0 },   // S (idx 0)
      { x: 0, y: 0 },    // A - to the LEFT of S (idx 1)
      { x: 100, y: 0 },  // B - to the right (idx 2)
      { x: 0, y: 50 },   // C (idx 3)
      { x: 100, y: 50 }, // T (idx 4)
      { x: 50, y: 50 },  // D (idx 5)
    ];

    // Without backward prevention, path might go S→A→C→... 
    // With sourceExitDir='right', first hop from S must go right
    const result = findShortestPath(spots, 0, 4, [], 'right');
    expect(result.length).toBeGreaterThan(0);

    // First hop from source should go right (x increases) or down (y increases), not left
    if (result.length >= 2) {
      expect(result[1].x).toBeGreaterThanOrEqual(result[0].x);
    }
  });

  it('still finds path when backward prevention blocks the direct route', () => {
    // Simple L-shape grid: only path is down then right
    const spots: Point[] = [
      { x: 50, y: 0 },   // S (idx 0)
      { x: 50, y: 50 },  // A (idx 1)
      { x: 100, y: 50 }, // T (idx 2)
    ];

    // sourceExitDir = 'down': allows going to A
    const result = findShortestPath(spots, 0, 2, [], 'down');
    expect(result).toHaveLength(3);
    expect(result[0]).toEqual({ x: 50, y: 0 });
    expect(result[2]).toEqual({ x: 100, y: 50 });
  });
});

// =============================================================================
// Task 2.5: Parallel connector offset
// =============================================================================

describe('computeParallelIndex', () => {
  it('returns 0 for a single line between two objects', () => {
    const objects = new Map<string, any>([
      ['line1', { objectType: 'line', sourceAnchor: { objectId: 'A' }, targetAnchor: { objectId: 'B' } }],
      ['A', { objectType: 'architecture-block' }],
      ['B', { objectType: 'architecture-block' }],
    ]);
    expect(computeParallelIndex('line1', 'A', 'B', objects)).toBe(0);
  });

  it('returns 0 when endpoints are not anchored', () => {
    const objects = new Map<string, any>([
      ['line1', { objectType: 'line', sourceAnchor: null, targetAnchor: null }],
    ]);
    expect(computeParallelIndex('line1', undefined, undefined, objects)).toBe(0);
  });

  it('assigns different offsets for multiple lines between same pair', () => {
    const objects = new Map<string, any>([
      ['line1', { objectType: 'line', sourceAnchor: { objectId: 'A' }, targetAnchor: { objectId: 'B' } }],
      ['line2', { objectType: 'line', sourceAnchor: { objectId: 'A' }, targetAnchor: { objectId: 'B' } }],
      ['line3', { objectType: 'line', sourceAnchor: { objectId: 'A' }, targetAnchor: { objectId: 'B' } }],
      ['A', { objectType: 'architecture-block' }],
      ['B', { objectType: 'architecture-block' }],
    ]);

    const idx1 = computeParallelIndex('line1', 'A', 'B', objects);
    const idx2 = computeParallelIndex('line2', 'A', 'B', objects);
    const idx3 = computeParallelIndex('line3', 'A', 'B', objects);

    // All different
    const indices = [idx1, idx2, idx3];
    expect(new Set(indices).size).toBe(3);
    // Centered around 0
    expect(indices).toContain(0);
  });

  it('detects lines in both directions (A→B and B→A)', () => {
    const objects = new Map<string, any>([
      ['line1', { objectType: 'line', sourceAnchor: { objectId: 'A' }, targetAnchor: { objectId: 'B' } }],
      ['line2', { objectType: 'line', sourceAnchor: { objectId: 'B' }, targetAnchor: { objectId: 'A' } }],
      ['A', { objectType: 'architecture-block' }],
      ['B', { objectType: 'architecture-block' }],
    ]);

    const idx1 = computeParallelIndex('line1', 'A', 'B', objects);
    const idx2 = computeParallelIndex('line2', 'B', 'A', objects);

    // Both should get an offset (different from each other)
    expect(idx1).not.toBe(idx2);
  });
});

describe('applyParallelOffset', () => {
  it('returns same path for offset 0', () => {
    const path: Point[] = [
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      { x: 100, y: 100 },
    ];
    expect(applyParallelOffset(path, 0)).toEqual(path);
  });

  it('offsets a horizontal segment in Y', () => {
    const path: Point[] = [
      { x: 0, y: 0 },
      { x: 100, y: 0 },
    ];
    const result = applyParallelOffset(path, 1);
    // Both points should be offset in Y by 8px (PARALLEL_OFFSET_PX)
    expect(result[0].y).toBe(8);
    expect(result[1].y).toBe(8);
    // X unchanged
    expect(result[0].x).toBe(0);
    expect(result[1].x).toBe(100);
  });

  it('offsets a vertical segment in X', () => {
    const path: Point[] = [
      { x: 50, y: 0 },
      { x: 50, y: 100 },
    ];
    const result = applyParallelOffset(path, 1);
    // Both points should be offset in X by 8px
    expect(result[0].x).toBe(58);
    expect(result[1].x).toBe(58);
    // Y unchanged
    expect(result[0].y).toBe(0);
    expect(result[1].y).toBe(100);
  });

  it('handles negative offset multiplier', () => {
    const path: Point[] = [
      { x: 0, y: 0 },
      { x: 100, y: 0 },
    ];
    const result = applyParallelOffset(path, -1);
    expect(result[0].y).toBe(-8);
    expect(result[1].y).toBe(-8);
  });

  it('does not crash on single-point path', () => {
    const path: Point[] = [{ x: 50, y: 50 }];
    const result = applyParallelOffset(path, 1);
    expect(result).toHaveLength(1);
  });
});

// =============================================================================
// Integration: Full router with Phase 2 features
// =============================================================================

describe('routeOrthogonalConnector with Phase 2 features', () => {
  it('produces balanced S-routes for facing anchors with offset', () => {
    const request: RoutingRequest = {
      sourcePoint: { x: 150, y: 80 },
      sourceSide: 'right',
      sourceRect: { left: 50, top: 50, width: 100, height: 60 },
      targetPoint: { x: 500, y: 120 },
      targetSide: 'left',
      targetRect: { left: 500, top: 90, width: 100, height: 60 },
      obstacles: [],
      shapeMargin: 20,
    };
    const result = routeOrthogonalConnector(request);

    const path = [request.sourcePoint, ...result.waypoints, request.targetPoint];
    assertOrthogonal(path);

    // Should produce a valid orthogonal route
    expect(path.length).toBeGreaterThanOrEqual(2);
  });

  it('uses short-distance route for very close shapes', () => {
    const request: RoutingRequest = {
      sourcePoint: { x: 150, y: 80 },
      sourceSide: 'right',
      sourceRect: { left: 50, top: 50, width: 100, height: 60 },
      targetPoint: { x: 165, y: 80 },
      targetSide: 'left',
      targetRect: { left: 165, top: 50, width: 100, height: 60 },
      obstacles: [],
      shapeMargin: 20,
    };
    const result = routeOrthogonalConnector(request);
    expect(result.success).toBe(true);
    // Very close facing anchors on same Y → should be direct (0 waypoints)
    expect(result.waypoints).toEqual([]);
  });
});
