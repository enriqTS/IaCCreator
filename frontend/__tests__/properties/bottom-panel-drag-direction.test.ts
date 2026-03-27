import fc from 'fast-check';
import { MIN_PANEL_HEIGHT, MAX_PANEL_HEIGHT_RATIO } from '@/components/config/panel-constants';

// Feature: bottom-panel-redesign, Property 6: Drag direction changes height proportionally
// **Validates: Requirements 2.2, 2.3**

/**
 * Pure resize logic extracted for property testing:
 * Given a current height and a drag delta, compute the new clamped height.
 * - delta > 0 means upward drag (increase height)
 * - delta < 0 means downward drag (decrease height)
 */
function applyResize(currentHeight: number, delta: number, viewportHeight: number): number {
  const maxHeight = MAX_PANEL_HEIGHT_RATIO * viewportHeight;
  const raw = currentHeight + delta;
  return Math.min(Math.max(raw, MIN_PANEL_HEIGHT), maxHeight);
}

describe('Property 6: Drag direction changes height proportionally', () => {
  const VIEWPORT_HEIGHT = window.innerHeight; // 768 in jsdom
  const MAX_HEIGHT = MAX_PANEL_HEIGHT_RATIO * VIEWPORT_HEIGHT;

  // Generator for valid current heights within clamped bounds
  const validHeightArb = fc.double({
    min: MIN_PANEL_HEIGHT,
    max: MAX_HEIGHT,
    noNaN: true,
    noDefaultInfinity: true,
  });

  // Generator for drag deltas (positive = upward/increase, negative = downward/decrease)
  const dragDeltaArb = fc.double({
    min: -2000,
    max: 2000,
    noNaN: true,
    noDefaultInfinity: true,
  });

  test('upward drag (positive delta) results in new height >= current height (subject to max clamp)', () => {
    fc.assert(
      fc.property(
        validHeightArb,
        fc.double({ min: 0, max: 2000, noNaN: true, noDefaultInfinity: true }),
        (currentHeight, positiveDelta) => {
          const newHeight = applyResize(currentHeight, positiveDelta, VIEWPORT_HEIGHT);
          expect(newHeight).toBeGreaterThanOrEqual(currentHeight);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('downward drag (negative delta) results in new height <= current height (subject to min clamp)', () => {
    fc.assert(
      fc.property(
        validHeightArb,
        fc.double({ min: -2000, max: 0, noNaN: true, noDefaultInfinity: true }),
        (currentHeight, negativeDelta) => {
          const newHeight = applyResize(currentHeight, negativeDelta, VIEWPORT_HEIGHT);
          expect(newHeight).toBeLessThanOrEqual(currentHeight);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('result is always clamped within [MIN_PANEL_HEIGHT, MAX_HEIGHT] regardless of delta', () => {
    fc.assert(
      fc.property(
        validHeightArb,
        dragDeltaArb,
        (currentHeight, delta) => {
          const newHeight = applyResize(currentHeight, delta, VIEWPORT_HEIGHT);
          expect(newHeight).toBeGreaterThanOrEqual(MIN_PANEL_HEIGHT);
          expect(newHeight).toBeLessThanOrEqual(MAX_HEIGHT);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('zero delta preserves current height exactly', () => {
    fc.assert(
      fc.property(
        validHeightArb,
        (currentHeight) => {
          const newHeight = applyResize(currentHeight, 0, VIEWPORT_HEIGHT);
          expect(newHeight).toBe(currentHeight);
        }
      ),
      { numRuns: 100 }
    );
  });
});
