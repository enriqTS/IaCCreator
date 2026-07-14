import { describe, it, expect } from 'vitest';
import { findShortestPath, simplifyPath, findSpotIndex } from '@/utils/routing/routing-pathfinder';
import type { ObstacleRect } from '@/utils/routing/routing-pathfinder';
import type { Point } from '@/types/diagram';

describe('simplifyPath', () => {
  it('returns empty array unchanged', () => {
    expect(simplifyPath([])).toEqual([]);
  });

  it('returns single point unchanged', () => {
    const pts: Point[] = [{ x: 1, y: 1 }];
    expect(simplifyPath(pts)).toEqual(pts);
  });

  it('returns two points unchanged', () => {
    const pts: Point[] = [{ x: 0, y: 0 }, { x: 10, y: 0 }];
    expect(simplifyPath(pts)).toEqual(pts);
  });

  it('removes collinear horizontal points', () => {
    const pts: Point[] = [
      { x: 0, y: 0 },
      { x: 5, y: 0 },
      { x: 10, y: 0 },
    ];
    expect(simplifyPath(pts)).toEqual([{ x: 0, y: 0 }, { x: 10, y: 0 }]);
  });

  it('removes collinear vertical points', () => {
    const pts: Point[] = [
      { x: 0, y: 0 },
      { x: 0, y: 5 },
      { x: 0, y: 10 },
    ];
    expect(simplifyPath(pts)).toEqual([{ x: 0, y: 0 }, { x: 0, y: 10 }]);
  });

  it('keeps bend points', () => {
    const pts: Point[] = [
      { x: 0, y: 0 },
      { x: 10, y: 0 },
      { x: 10, y: 10 },
    ];
    expect(simplifyPath(pts)).toEqual(pts);
  });

  it('removes multiple collinear points in a row', () => {
    const pts: Point[] = [
      { x: 0, y: 0 },
      { x: 2, y: 0 },
      { x: 5, y: 0 },
      { x: 8, y: 0 },
      { x: 10, y: 0 },
      { x: 10, y: 5 },
      { x: 10, y: 10 },
    ];
    const result = simplifyPath(pts);
    expect(result).toEqual([
      { x: 0, y: 0 },
      { x: 10, y: 0 },
      { x: 10, y: 10 },
    ]);
  });
});

describe('findSpotIndex', () => {
  const spots: Point[] = [
    { x: 0, y: 0 },
    { x: 10, y: 0 },
    { x: 10, y: 10 },
    { x: 0, y: 10 },
  ];

  it('finds an existing point', () => {
    expect(findSpotIndex(spots, { x: 10, y: 10 })).toBe(2);
  });

  it('returns first match', () => {
    expect(findSpotIndex(spots, { x: 0, y: 0 })).toBe(0);
  });

  it('returns -1 for non-existent point', () => {
    expect(findSpotIndex(spots, { x: 5, y: 5 })).toBe(-1);
  });
});

describe('findShortestPath', () => {
  it('returns single point when source === target', () => {
    const spots: Point[] = [{ x: 0, y: 0 }, { x: 10, y: 0 }];
    const result = findShortestPath(spots, 0, 0);
    expect(result).toEqual([{ x: 0, y: 0 }]);
  });

  it('finds a direct horizontal path', () => {
    // Simple grid: 3 points on same Y
    const spots: Point[] = [
      { x: 0, y: 0 },
      { x: 50, y: 0 },
      { x: 100, y: 0 },
    ];
    const result = findShortestPath(spots, 0, 2);
    expect(result.length).toBeGreaterThanOrEqual(2);
    expect(result[0]).toEqual({ x: 0, y: 0 });
    expect(result[result.length - 1]).toEqual({ x: 100, y: 0 });
  });

  it('finds a direct vertical path', () => {
    const spots: Point[] = [
      { x: 0, y: 0 },
      { x: 0, y: 50 },
      { x: 0, y: 100 },
    ];
    const result = findShortestPath(spots, 0, 2);
    expect(result[0]).toEqual({ x: 0, y: 0 });
    expect(result[result.length - 1]).toEqual({ x: 0, y: 100 });
  });

  it('finds an L-shaped path when needed', () => {
    // Grid forming an L:
    //  A --- B
    //        |
    //        C
    const spots: Point[] = [
      { x: 0, y: 0 },   // A (index 0)
      { x: 100, y: 0 },  // B (index 1)
      { x: 100, y: 100 }, // C (index 2)
    ];
    const result = findShortestPath(spots, 0, 2);
    expect(result).toHaveLength(3);
    expect(result[0]).toEqual({ x: 0, y: 0 });
    expect(result[1]).toEqual({ x: 100, y: 0 });
    expect(result[2]).toEqual({ x: 100, y: 100 });
  });

  it('avoids obstacles by not creating blocked edges', () => {
    // Grid:
    //  S ---(obstacle)--- X
    //  |                  |
    //  A ---- B --------- T
    //
    // Spots forming a detour path around obstacle
    const spots: Point[] = [
      { x: 0, y: 0 },    // S (source, idx 0)
      { x: 100, y: 0 },  // X (idx 1) — direct horizontal is blocked
      { x: 0, y: 100 },  // A (idx 2)
      { x: 50, y: 100 }, // B (idx 3)
      { x: 100, y: 100 },// T (target, idx 4)
    ];

    // Obstacle blocks the horizontal segment at y=0 between x=0 and x=100
    const obstacles: ObstacleRect[] = [
      { left: 30, top: -10, width: 40, height: 20 }, // blocks y=0, x=[30,70]
    ];

    const result = findShortestPath(spots, 0, 4, obstacles);
    expect(result.length).toBeGreaterThan(0);
    expect(result[0]).toEqual({ x: 0, y: 0 });
    expect(result[result.length - 1]).toEqual({ x: 100, y: 100 });

    // Should NOT go through the blocked direct route (0,0) → (100,0)
    // Path should go via y=100
    const goesViaBottom = result.some((p) => p.y === 100);
    expect(goesViaBottom).toBe(true);
  });

  it('returns empty array when no path exists', () => {
    // Two disconnected spots (no shared X or Y coordinate → no edges)
    const spots: Point[] = [
      { x: 0, y: 0 },
      { x: 50, y: 50 },
    ];
    const result = findShortestPath(spots, 0, 1);
    expect(result).toEqual([]);
  });

  it('prefers fewer bends due to bend penalty', () => {
    // Grid where a straight path and an L-shaped path both reach target
    // Straight: S → A → T (all same Y = 0, 2 segments, 0 bends)
    // L-shaped: S → B → C → T (goes down and back up, 2 bends)
    const spots: Point[] = [
      { x: 0, y: 0 },    // S (idx 0)
      { x: 50, y: 0 },   // A (idx 1)
      { x: 100, y: 0 },  // T (idx 2)
      { x: 0, y: 50 },   // B (idx 3)
      { x: 100, y: 50 }, // C (idx 4)
    ];
    const result = findShortestPath(spots, 0, 2);
    // Should prefer the straight route
    expect(result).toEqual([
      { x: 0, y: 0 },
      { x: 50, y: 0 },
      { x: 100, y: 0 },
    ]);
  });
});
