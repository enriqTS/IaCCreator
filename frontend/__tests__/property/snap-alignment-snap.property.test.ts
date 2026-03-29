/**
 * Property-based test: Alignment snap produces exact alignment
 *
 * Feature: canvas-snap-to-grid, Property 6: Alignment snap produces exact alignment
 *
 * **Validates: Requirements 3.3**
 *
 * For any position and set of alignment guides, applyAlignmentSnap(position, guides)
 * shall return a position where the corresponding coordinate is adjusted by the
 * smallest snapDelta for each axis. For a horizontal guide with snapDelta d,
 * result.y === position.y + d. For a vertical guide with snapDelta d,
 * result.x === position.x + d.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { applyAlignmentSnap } from '@/utils/snap';
import type { AlignmentGuide } from '@/utils/snap';
import type { Point } from '@/types/diagram';

/** Arbitrary for coordinate values. */
const coordinateArb = fc.double({
  min: -10000,
  max: 10000,
  noNaN: true,
  noDefaultInfinity: true,
});

/** Arbitrary for a canvas Point. */
const pointArb: fc.Arbitrary<Point> = fc.record({
  x: coordinateArb,
  y: coordinateArb,
});

/** Arbitrary for a single AlignmentGuide. */
const guideArb: fc.Arbitrary<AlignmentGuide> = fc.record({
  axis: fc.constantFrom('horizontal' as const, 'vertical' as const),
  position: coordinateArb,
  from: coordinateArb,
  to: coordinateArb,
  snapDelta: fc.double({ min: -500, max: 500, noNaN: true, noDefaultInfinity: true }),
});

/** Arbitrary for a non-empty array of guides. */
const guidesArb = fc.array(guideArb, { minLength: 1, maxLength: 10 });

/**
 * Helper: find the guide with the smallest |snapDelta| for a given axis.
 */
function findSmallestDeltaGuide(
  guides: AlignmentGuide[],
  axis: 'horizontal' | 'vertical',
): AlignmentGuide | undefined {
  const axisGuides = guides.filter((g) => g.axis === axis);
  if (axisGuides.length === 0) return undefined;
  return axisGuides.reduce((best, g) =>
    Math.abs(g.snapDelta) < Math.abs(best.snapDelta) ? g : best,
  );
}

describe('Feature: canvas-snap-to-grid, Property 6: Alignment snap produces exact alignment', () => {
  it('result coordinate equals position + smallest snapDelta for each axis', () => {
    /**
     * **Validates: Requirements 3.3**
     *
     * Strategy: Generate random positions and guide arrays. For each axis,
     * find the guide with the smallest |snapDelta|. Verify the result
     * coordinate matches position + that snapDelta.
     */
    fc.assert(
      fc.property(pointArb, guidesArb, (position, guides) => {
        const result = applyAlignmentSnap(position, guides);

        const bestHorizontal = findSmallestDeltaGuide(guides, 'horizontal');
        const bestVertical = findSmallestDeltaGuide(guides, 'vertical');

        if (bestHorizontal) {
          expect(result.y).toBeCloseTo(position.y + bestHorizontal.snapDelta, 9);
        } else {
          expect(result.y).toBeCloseTo(position.y, 9);
        }

        if (bestVertical) {
          expect(result.x).toBeCloseTo(position.x + bestVertical.snapDelta, 9);
        } else {
          expect(result.x).toBeCloseTo(position.x, 9);
        }
      }),
      { numRuns: 100 },
    );
  });

  it('returns position unchanged when guides array is empty', () => {
    /**
     * **Validates: Requirements 3.3**
     *
     * Edge case: with no guides, the position should be returned unchanged.
     */
    fc.assert(
      fc.property(pointArb, (position) => {
        const result = applyAlignmentSnap(position, []);
        expect(result.x).toBeCloseTo(position.x, 9);
        expect(result.y).toBeCloseTo(position.y, 9);
      }),
      { numRuns: 100 },
    );
  });
});
