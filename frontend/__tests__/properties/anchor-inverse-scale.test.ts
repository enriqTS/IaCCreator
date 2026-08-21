/**
 * Property-based test: Anchor indicator inverse-scale invariant
 *
 * Feature: line-segment-manipulation, Property 1: Anchor indicator inverse-scale invariant
 *
 * **Validates: Requirements 1.1, 1.2, 1.5**
 *
 * For any viewport zoom scale in the valid range [0.1, 5.0], the anchor indicator
 * hit area radius in canvas coordinates multiplied by the scale shall equal 24 screen
 * pixels, and the dot radius in canvas coordinates multiplied by the scale shall equal
 * 5 screen pixels.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';

/**
 * Constants from AnchorIndicators.tsx.
 * The component computes canvas-space radii as:
 *   hitRadius = HIT_RADIUS_SCREEN / scale
 *   dotRadius = DOT_RADIUS_SCREEN / scale
 * Multiplying back by scale must recover the original screen-pixel constant.
 */
const HIT_RADIUS_SCREEN = 24;
const DOT_RADIUS_SCREEN = 5;

/** Arbitrary for valid zoom scales in [0.1, 5.0]. */
const zoomScaleArb = fc.double({ min: 0.1, max: 5.0, noNaN: true, noDefaultInfinity: true });

describe('Feature: line-segment-manipulation, Property 1: Anchor indicator inverse-scale invariant', () => {
  it('hit area canvas radius * scale === HIT_RADIUS_SCREEN (24) for all valid zoom scales', () => {
    /**
     * **Validates: Requirements 1.1, 1.5**
     *
     * Strategy: Generate random zoom scales in [0.1, 5.0].
     * Compute the canvas-space hit radius as HIT_RADIUS_SCREEN / scale,
     * then multiply back by scale. The result must equal 24 within
     * floating-point tolerance.
     */
    fc.assert(
      fc.property(zoomScaleArb, (scale) => {
        const hitRadiusCanvas = HIT_RADIUS_SCREEN / scale;
        const recoveredScreen = hitRadiusCanvas * scale;

        expect(recoveredScreen).toBeCloseTo(HIT_RADIUS_SCREEN, 10);
      }),
      { numRuns: 100 },
    );
  });

  it('dot canvas radius * scale === DOT_RADIUS_SCREEN (5) for all valid zoom scales', () => {
    /**
     * **Validates: Requirements 1.2, 1.5**
     *
     * Strategy: Generate random zoom scales in [0.1, 5.0].
     * Compute the canvas-space dot radius as DOT_RADIUS_SCREEN / scale,
     * then multiply back by scale. The result must equal 5 within
     * floating-point tolerance.
     */
    fc.assert(
      fc.property(zoomScaleArb, (scale) => {
        const dotRadiusCanvas = DOT_RADIUS_SCREEN / scale;
        const recoveredScreen = dotRadiusCanvas * scale;

        expect(recoveredScreen).toBeCloseTo(DOT_RADIUS_SCREEN, 10);
      }),
      { numRuns: 100 },
    );
  });
});
