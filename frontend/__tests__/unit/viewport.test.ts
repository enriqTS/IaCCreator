import { describe, it, expect } from 'vitest';
import { screenToCanvas, canvasToScreen, zoomAtPoint, clamp } from '@/utils/viewport';
import type { Viewport, Point } from '@/types/diagram';

describe('clamp', () => {
  it('returns value when within range', () => {
    expect(clamp(5, 0, 10)).toBe(5);
  });

  it('clamps to min when value is below', () => {
    expect(clamp(-1, 0, 10)).toBe(0);
  });

  it('clamps to max when value is above', () => {
    expect(clamp(15, 0, 10)).toBe(10);
  });

  it('returns min when min equals max', () => {
    expect(clamp(5, 3, 3)).toBe(3);
  });
});

describe('screenToCanvas', () => {
  it('returns the same point with identity viewport', () => {
    const viewport: Viewport = { offsetX: 0, offsetY: 0, scale: 1.0 };
    const screen: Point = { x: 150, y: 250 };
    const result = screenToCanvas(screen, viewport);
    expect(result.x).toBe(150);
    expect(result.y).toBe(250);
  });

  it('divides by scale with zoomed viewport', () => {
    const viewport: Viewport = { offsetX: 0, offsetY: 0, scale: 2.0 };
    const screen: Point = { x: 200, y: 200 };
    const result = screenToCanvas(screen, viewport);
    expect(result.x).toBe(100);
    expect(result.y).toBe(100);
  });

  it('subtracts offset with panned viewport', () => {
    const viewport: Viewport = { offsetX: 100, offsetY: 50, scale: 1.0 };
    const screen: Point = { x: 200, y: 150 };
    const result = screenToCanvas(screen, viewport);
    expect(result.x).toBe(100);
    expect(result.y).toBe(100);
  });
});

describe('canvasToScreen', () => {
  it('returns the same point with identity viewport', () => {
    const viewport: Viewport = { offsetX: 0, offsetY: 0, scale: 1.0 };
    const canvas: Point = { x: 150, y: 250 };
    const result = canvasToScreen(canvas, viewport);
    expect(result.x).toBe(150);
    expect(result.y).toBe(250);
  });

  it('multiplies by scale with zoomed viewport', () => {
    const viewport: Viewport = { offsetX: 0, offsetY: 0, scale: 2.0 };
    const canvas: Point = { x: 100, y: 100 };
    const result = canvasToScreen(canvas, viewport);
    expect(result.x).toBe(200);
    expect(result.y).toBe(200);
  });

  it('adds offset with panned viewport', () => {
    const viewport: Viewport = { offsetX: 100, offsetY: 50, scale: 1.0 };
    const canvas: Point = { x: 100, y: 100 };
    const result = canvasToScreen(canvas, viewport);
    expect(result.x).toBe(200);
    expect(result.y).toBe(150);
  });
});

describe('zoomAtPoint', () => {
  it('clamps scale to minimum 0.1', () => {
    const viewport: Viewport = { offsetX: 0, offsetY: 0, scale: 0.2 };
    const center: Point = { x: 400, y: 300 };
    const result = zoomAtPoint(viewport, 0.1, center);
    expect(result.scale).toBeCloseTo(0.1, 5);
  });

  it('clamps scale to maximum 5.0', () => {
    const viewport: Viewport = { offsetX: 0, offsetY: 0, scale: 4.0 };
    const center: Point = { x: 400, y: 300 };
    const result = zoomAtPoint(viewport, 2.0, center);
    expect(result.scale).toBeCloseTo(5.0, 5);
  });

  it('preserves the canvas point under the cursor after zoom', () => {
    const viewport: Viewport = { offsetX: 50, offsetY: 30, scale: 1.0 };
    const center: Point = { x: 400, y: 300 };

    const canvasBefore = screenToCanvas(center, viewport);
    const zoomed = zoomAtPoint(viewport, 1.5, center);
    const canvasAfter = screenToCanvas(center, zoomed);

    expect(canvasAfter.x).toBeCloseTo(canvasBefore.x, 5);
    expect(canvasAfter.y).toBeCloseTo(canvasBefore.y, 5);
  });
});
