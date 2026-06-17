import { describe, it, expect } from 'vitest';
import { getShapeTightBounds } from '@/utils/bounds-utils';

describe('getShapeTightBounds', () => {
  describe('circle/ellipse shapes', () => {
    it('returns bounds matching the full width/height for a circle with no border', () => {
      const result = getShapeTightBounds('circle', 100, 100, 0);
      expect(result).toEqual({ x: 0, y: 0, width: 100, height: 100 });
    });

    it('expands bounds by borderWidth/2 on each side for a circle', () => {
      const result = getShapeTightBounds('circle', 100, 100, 4);
      expect(result).toEqual({ x: -2, y: -2, width: 104, height: 104 });
    });

    it('returns bounds matching the full width/height for an ellipse with no border', () => {
      const result = getShapeTightBounds('ellipse', 120, 80, 0);
      expect(result).toEqual({ x: 0, y: 0, width: 120, height: 80 });
    });

    it('expands bounds by borderWidth/2 on each side for an ellipse', () => {
      const result = getShapeTightBounds('ellipse', 120, 80, 6);
      expect(result).toEqual({ x: -3, y: -3, width: 126, height: 86 });
    });
  });

  describe('polygon shapes', () => {
    it('computes tight bounds for a rectangle with no border', () => {
      const result = getShapeTightBounds('rectangle', 100, 60, 0);
      expect(result).toEqual({ x: 0, y: 0, width: 100, height: 60 });
    });

    it('expands rectangle bounds by borderWidth/2', () => {
      const result = getShapeTightBounds('rectangle', 100, 60, 4);
      expect(result).toEqual({ x: -2, y: -2, width: 104, height: 64 });
    });

    it('computes tight bounds for a triangle', () => {
      // Triangle: M w/2 0, L w h, L 0 h — vertices at (50,0), (100,60), (0,60)
      const result = getShapeTightBounds('triangle', 100, 60, 0);
      expect(result.x).toBe(0);
      expect(result.y).toBe(0);
      expect(result.width).toBe(100);
      expect(result.height).toBe(60);
    });

    it('expands triangle bounds by borderWidth/2', () => {
      const result = getShapeTightBounds('triangle', 100, 60, 4);
      expect(result.x).toBe(-2);
      expect(result.y).toBe(-2);
      expect(result.width).toBe(104);
      expect(result.height).toBe(64);
    });

    it('computes tight bounds for a diamond', () => {
      // Diamond: M w/2 0, L w h/2, L w/2 h, L 0 h/2
      const result = getShapeTightBounds('diamond', 100, 80, 0);
      expect(result.x).toBe(0);
      expect(result.y).toBe(0);
      expect(result.width).toBe(100);
      expect(result.height).toBe(80);
    });

    it('computes tight bounds for a star', () => {
      const result = getShapeTightBounds('star', 100, 100, 0);
      // Star outer vertices reach near the bounding box edges but may not hit exact corners
      // The top vertex is at (50, 0) and the bottom outer vertices reach near y=100
      expect(result.y).toBeCloseTo(0, 0);
      expect(result.height).toBeGreaterThan(90);
      expect(result.width).toBeGreaterThan(90);
      // Bounds should not extend beyond the original bounding box
      expect(result.x).toBeGreaterThanOrEqual(0);
      expect(result.y).toBeGreaterThanOrEqual(0);
    });

    it('computes tight bounds for a hexagon', () => {
      // Hexagon spans full width and height
      const result = getShapeTightBounds('hexagon', 120, 80, 0);
      expect(result.x).toBe(0);
      expect(result.y).toBe(0);
      expect(result.width).toBe(120);
      expect(result.height).toBe(80);
    });
  });

  describe('stroke width contribution', () => {
    it('bounds with borderWidth > 0 are exactly borderWidth larger in each dimension', () => {
      const shapes = ['rectangle', 'triangle', 'diamond', 'hexagon', 'circle', 'ellipse'] as const;
      for (const shape of shapes) {
        const noBorder = getShapeTightBounds(shape, 100, 80, 0);
        const withBorder = getShapeTightBounds(shape, 100, 80, 6);
        expect(withBorder.width).toBeCloseTo(noBorder.width + 6, 5);
        expect(withBorder.height).toBeCloseTo(noBorder.height + 6, 5);
      }
    });
  });

  describe('fallback behavior', () => {
    it('returns rectangle bounds for an unknown shape', () => {
      // Cast to test fallback with a shape not in registry
      const result = getShapeTightBounds('nonexistent-shape' as any, 100, 60, 4);
      expect(result).toEqual({ x: -2, y: -2, width: 104, height: 64 });
    });
  });

  describe('curved shapes', () => {
    it('computes bounds for cloud shape within expected dimensions', () => {
      const result = getShapeTightBounds('cloud', 200, 150, 0);
      // Cloud has control points that may extend slightly; bounds should
      // still be within or very close to the bounding box
      expect(result.x).toBeGreaterThanOrEqual(-1);
      expect(result.y).toBeGreaterThanOrEqual(-1);
      expect(result.width).toBeLessThanOrEqual(202);
      expect(result.height).toBeLessThanOrEqual(152);
    });

    it('computes bounds for rounded-rectangle', () => {
      const result = getShapeTightBounds('rounded-rectangle', 100, 60, 0);
      // Rounded rectangle should still span essentially the full width/height
      expect(result.x).toBeCloseTo(0, 0);
      expect(result.y).toBeCloseTo(0, 0);
      expect(result.width).toBeCloseTo(100, 0);
      expect(result.height).toBeCloseTo(60, 0);
    });

    it('computes bounds for cylinder', () => {
      const result = getShapeTightBounds('cylinder', 100, 100, 0);
      // Cylinder has arc elements; bounds should cover the shape
      expect(result.x).toBeGreaterThanOrEqual(-1);
      expect(result.y).toBeGreaterThanOrEqual(-1);
      expect(result.width).toBeGreaterThanOrEqual(98);
      expect(result.height).toBeGreaterThanOrEqual(98);
    });
  });
});
