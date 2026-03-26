/**
 * Property-based test: Viewport transform consistency
 *
 * **Validates: Requirements 4.1, 4.2, 4.3**
 *
 * Property 6: Object positions in canvas coordinates are invariant under
 * viewport pan/zoom — applying canvasToScreen then screenToCanvas (the inverse)
 * yields the original position within floating-point tolerance.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { canvasToScreen, screenToCanvas } from '@/utils/viewport';
import { pointArbitrary, viewportArbitrary } from '../properties/arbitraries';

const EPSILON = 1e-6;

describe('Viewport Transform Consistency Property', () => {
  it('Property 6: canvasToScreen then screenToCanvas is the identity (round-trip)', () => {
    /**
     * **Validates: Requirements 4.1, 4.2, 4.3**
     *
     * For any canvas point and any valid viewport state, converting
     * canvas → screen → canvas must return the original canvas point.
     */
    fc.assert(
      fc.property(pointArbitrary(), viewportArbitrary(), (canvasPoint, viewport) => {
        const screenPoint = canvasToScreen(canvasPoint, viewport);
        const roundTripped = screenToCanvas(screenPoint, viewport);

        expect(roundTripped.x).toBeCloseTo(canvasPoint.x, 5);
        expect(roundTripped.y).toBeCloseTo(canvasPoint.y, 5);
      }),
      { numRuns: 500 },
    );
  });

  it('Property 6b: screenToCanvas then canvasToScreen is the identity (reverse round-trip)', () => {
    /**
     * **Validates: Requirements 4.1, 4.2, 4.3**
     *
     * The inverse direction must also hold: converting
     * screen → canvas → screen returns the original screen point.
     */
    fc.assert(
      fc.property(pointArbitrary(), viewportArbitrary(), (screenPoint, viewport) => {
        const canvasPoint = screenToCanvas(screenPoint, viewport);
        const roundTripped = canvasToScreen(canvasPoint, viewport);

        expect(roundTripped.x).toBeCloseTo(screenPoint.x, 5);
        expect(roundTripped.y).toBeCloseTo(screenPoint.y, 5);
      }),
      { numRuns: 500 },
    );
  });
});
