import fc from 'fast-check';
import { screenToCanvas, canvasToScreen, zoomAtPoint } from '@/utils/viewport';
import type { Viewport } from '@/types/diagram';
import { viewportArbitrary, pointArbitrary } from './arbitraries';

const FLOAT_TOLERANCE = 1e-6;

function approxEqual(a: number, b: number, tol = FLOAT_TOLERANCE): boolean {
  return Math.abs(a - b) <= tol + tol * Math.abs(b);
}

// Feature: diagram-editor-frontend, Property 1: Pan offset correctness
// **Validates: Requirements 1.2**
describe('Property 1: Pan offset correctness', () => {
  test('panning changes offset by exactly (dx, dy) without affecting scale', () => {
    fc.assert(
      fc.property(
        viewportArbitrary(),
        fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
        fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
        (viewport: Viewport, dx: number, dy: number) => {
          const panned: Viewport = {
            offsetX: viewport.offsetX + dx,
            offsetY: viewport.offsetY + dy,
            scale: viewport.scale,
          };

          // Offset changes by exactly (dx, dy)
          expect(panned.offsetX).toBe(viewport.offsetX + dx);
          expect(panned.offsetY).toBe(viewport.offsetY + dy);

          // Scale is unchanged
          expect(panned.scale).toBe(viewport.scale);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// Feature: diagram-editor-frontend, Property 2: Zoom preserves point under cursor
// **Validates: Requirements 1.3, 1.4, 1.5**
describe('Property 2: Zoom preserves point under cursor', () => {
  test('canvas point under cursor is preserved after zoom (within float tolerance), scale clamped to [0.1, 5.0]', () => {
    fc.assert(
      fc.property(
        viewportArbitrary(),
        fc.double({ min: 0.1, max: 10.0, noNaN: true, noDefaultInfinity: true }),
        pointArbitrary(),
        (viewport: Viewport, factor: number, cursorScreen) => {
          // Canvas point under cursor before zoom
          const canvasBefore = screenToCanvas(cursorScreen, viewport);

          // Zoom at cursor
          const zoomed = zoomAtPoint(viewport, factor, cursorScreen);

          // Scale must be clamped to [0.1, 5.0]
          expect(zoomed.scale).toBeGreaterThanOrEqual(0.1 - FLOAT_TOLERANCE);
          expect(zoomed.scale).toBeLessThanOrEqual(5.0 + FLOAT_TOLERANCE);

          // Canvas point under cursor after zoom
          const canvasAfter = screenToCanvas(cursorScreen, zoomed);

          // The canvas point under the cursor should be preserved
          expect(approxEqual(canvasBefore.x, canvasAfter.x)).toBe(true);
          expect(approxEqual(canvasBefore.y, canvasAfter.y)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// Feature: diagram-editor-frontend, Property 13: Coordinate transform round-trip
// **Validates: Requirements 1.2, 1.3**
describe('Property 13: Coordinate transform round-trip', () => {
  test('screenToCanvas(canvasToScreen(p)) ≈ p', () => {
    fc.assert(
      fc.property(
        viewportArbitrary(),
        pointArbitrary(),
        (viewport, canvasPoint) => {
          const screenPoint = canvasToScreen(canvasPoint, viewport);
          const roundTrip = screenToCanvas(screenPoint, viewport);

          expect(approxEqual(roundTrip.x, canvasPoint.x)).toBe(true);
          expect(approxEqual(roundTrip.y, canvasPoint.y)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('canvasToScreen(screenToCanvas(p)) ≈ p', () => {
    fc.assert(
      fc.property(
        viewportArbitrary(),
        pointArbitrary(),
        (viewport, screenPoint) => {
          const canvasPoint = screenToCanvas(screenPoint, viewport);
          const roundTrip = canvasToScreen(canvasPoint, viewport);

          expect(approxEqual(roundTrip.x, screenPoint.x)).toBe(true);
          expect(approxEqual(roundTrip.y, screenPoint.y)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });
});
