/**
 * Unit tests for snap utility edge cases.
 *
 * Feature: canvas-snap-to-grid, Task 1.7
 * Requirements: 1.1, 1.2, 1.3, 3.1, 3.5, 4.1, 4.2
 */
import { describe, it, expect } from 'vitest';
import {
  snapToGrid,
  snapDimension,
  detectAlignmentGuides,
  clampToViewport,
} from '@/utils/snap';
import type { Rect } from '@/types/diagram';

describe('snapToGrid edge cases', () => {
  it('returns 0 for snapToGrid(0, 20)', () => {
    expect(snapToGrid(0, 20)).toBe(0);
  });

  it('rounds up: snapToGrid(11, 20) returns 20', () => {
    expect(snapToGrid(11, 20)).toBe(20);
  });

  it('rounds down: snapToGrid(9, 20) returns 0', () => {
    expect(snapToGrid(9, 20)).toBe(0);
  });

  it('returns input unchanged when gridSize is 0', () => {
    expect(snapToGrid(15, 0)).toBe(15);
  });

  it('returns input unchanged when gridSize is negative', () => {
    expect(snapToGrid(42, -10)).toBe(42);
  });
});

describe('snapDimension edge cases', () => {
  it('enforces minimum: snapDimension(5, 20) returns 20', () => {
    expect(snapDimension(5, 20)).toBe(20);
  });

  it('enforces minimum for zero input: snapDimension(0, 20) returns 20', () => {
    expect(snapDimension(0, 20)).toBe(20);
  });
});

describe('detectAlignmentGuides edge cases', () => {
  it('returns a guide when two rects share an exact edge', () => {
    const dragged: Rect = { x: 0, y: 0, width: 50, height: 50 };
    // other rect's left edge (100) is exactly at dragged right edge (50) — not aligned.
    // Instead, align top edges exactly (both y = 0).
    const other: Rect = { x: 100, y: 0, width: 50, height: 50 };
    const guides = detectAlignmentGuides(dragged, [other], 5);
    // Top edges match (both at y=0), bottom edges match (both at y=50),
    // and vertical centers match (both at y=25) — all horizontal guides.
    const horizontalGuides = guides.filter((g) => g.axis === 'horizontal');
    expect(horizontalGuides.length).toBeGreaterThan(0);
    // At least one guide should have snapDelta of 0 (exact match)
    expect(horizontalGuides.some((g) => g.snapDelta === 0)).toBe(true);
  });

  it('returns no guides when rects are far apart', () => {
    const dragged: Rect = { x: 0, y: 0, width: 50, height: 50 };
    const other: Rect = { x: 500, y: 500, width: 50, height: 50 };
    const guides = detectAlignmentGuides(dragged, [other], 5);
    expect(guides).toHaveLength(0);
  });
});

describe('clampToViewport edge cases', () => {
  it('clamps an out-of-bounds point to a grid-aligned position within viewport', () => {
    const viewport: Rect = { x: 0, y: 0, width: 200, height: 200 };
    // Point is outside the viewport on both axes
    const result = clampToViewport({ x: 300, y: -50 }, 20, viewport);
    // x should be clamped to viewport max (200), then snapped to grid → 200
    expect(result.x).toBe(200);
    // y should be clamped to viewport min (0), then snapped to grid → 0
    expect(result.y).toBe(0);
    // Both should be grid-aligned
    expect(result.x % 20).toBe(0);
    expect(result.y % 20).toBe(0);
  });
});
