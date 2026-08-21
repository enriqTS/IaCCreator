/**
 * Property-based test: Alignment detection is threshold-bounded
 *
 * Feature: canvas-snap-to-grid, Property 5: Alignment detection is threshold-bounded
 *
 * **Validates: Requirements 3.1, 3.5**
 *
 * For any two bounding rectangles where a corresponding edge or center pair has
 * distance d, detectAlignmentGuides shall return a guide for that pair if and
 * only if d <= threshold. When d > threshold, no guide shall be returned for
 * that pair.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { detectAlignmentGuides } from '@/utils/snap';
import type { Rect } from '@/types/diagram';

/** Arbitrary for a positive dimension (width/height). */
const dimensionArb = fc.double({ min: 1, max: 500, noNaN: true, noDefaultInfinity: true });

/** Arbitrary for a coordinate value. */
const coordinateArb = fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true });

/** Arbitrary for a threshold value. */
const thresholdArb = fc.double({ min: 0.1, max: 50, noNaN: true, noDefaultInfinity: true });

/** Arbitrary for a Rect with positive dimensions. */
const rectArb: fc.Arbitrary<Rect> = fc.record({
  x: coordinateArb,
  y: coordinateArb,
  width: dimensionArb,
  height: dimensionArb,
});

/**
 * Given two rects, compute the 6 alignment distances:
 * top, bottom, vertical-center, left, right, horizontal-center.
 */
function computeAlignmentDistances(dragged: Rect, other: Rect) {
  return {
    top: Math.abs(other.y - dragged.y),
    bottom: Math.abs((other.y + other.height) - (dragged.y + dragged.height)),
    verticalCenter: Math.abs((other.y + other.height / 2) - (dragged.y + dragged.height / 2)),
    left: Math.abs(other.x - dragged.x),
    right: Math.abs((other.x + other.width) - (dragged.x + dragged.width)),
    horizontalCenter: Math.abs((other.x + other.width / 2) - (dragged.x + dragged.width / 2)),
  };
}

describe('Feature: canvas-snap-to-grid, Property 5: Alignment detection is threshold-bounded', () => {
  it('returns a guide for each alignment type iff distance <= threshold', () => {
    /**
     * **Validates: Requirements 3.1, 3.5**
     *
     * Strategy: Generate random rect pairs and a threshold. For each of the 6
     * alignment types, compute the distance between corresponding edges/centers.
     * Verify that detectAlignmentGuides returns a guide for that type if and
     * only if the distance is within the threshold.
     */
    fc.assert(
      fc.property(rectArb, rectArb, thresholdArb, (dragged, other, threshold) => {
        const guides = detectAlignmentGuides(dragged, [other], threshold);
        const distances = computeAlignmentDistances(dragged, other);

        // Compute expected snap deltas for each alignment type
        const expectedDeltas = {
          top: other.y - dragged.y,
          bottom: (other.y + other.height) - (dragged.y + dragged.height),
          verticalCenter: (other.y + other.height / 2) - (dragged.y + dragged.height / 2),
          left: other.x - dragged.x,
          right: (other.x + other.width) - (dragged.x + dragged.width),
          horizontalCenter: (other.x + other.width / 2) - (dragged.x + dragged.width / 2),
        };

        // --- Horizontal guides (y-axis alignments): top, bottom, vertical-center ---
        const horizontalGuides = guides.filter((g) => g.axis === 'horizontal');

        // Check top alignment
        const topGuide = horizontalGuides.find(
          (g) => Math.abs(g.snapDelta - expectedDeltas.top) < 1e-9,
        );
        if (distances.top <= threshold) {
          expect(topGuide).toBeDefined();
        } else {
          expect(topGuide).toBeUndefined();
        }

        // Check bottom alignment
        const bottomGuide = horizontalGuides.find(
          (g) => Math.abs(g.snapDelta - expectedDeltas.bottom) < 1e-9,
        );
        if (distances.bottom <= threshold) {
          expect(bottomGuide).toBeDefined();
        } else {
          expect(bottomGuide).toBeUndefined();
        }

        // Check vertical-center alignment
        const vCenterGuide = horizontalGuides.find(
          (g) => Math.abs(g.snapDelta - expectedDeltas.verticalCenter) < 1e-9,
        );
        if (distances.verticalCenter <= threshold) {
          expect(vCenterGuide).toBeDefined();
        } else {
          expect(vCenterGuide).toBeUndefined();
        }

        // --- Vertical guides (x-axis alignments): left, right, horizontal-center ---
        const verticalGuides = guides.filter((g) => g.axis === 'vertical');

        // Check left alignment
        const leftGuide = verticalGuides.find(
          (g) => Math.abs(g.snapDelta - expectedDeltas.left) < 1e-9,
        );
        if (distances.left <= threshold) {
          expect(leftGuide).toBeDefined();
        } else {
          expect(leftGuide).toBeUndefined();
        }

        // Check right alignment
        const rightGuide = verticalGuides.find(
          (g) => Math.abs(g.snapDelta - expectedDeltas.right) < 1e-9,
        );
        if (distances.right <= threshold) {
          expect(rightGuide).toBeDefined();
        } else {
          expect(rightGuide).toBeUndefined();
        }

        // Check horizontal-center alignment
        const hCenterGuide = verticalGuides.find(
          (g) => Math.abs(g.snapDelta - expectedDeltas.horizontalCenter) < 1e-9,
        );
        if (distances.horizontalCenter <= threshold) {
          expect(hCenterGuide).toBeDefined();
        } else {
          expect(hCenterGuide).toBeUndefined();
        }
      }),
      { numRuns: 100 },
    );
  });

  it('returns no guides when otherBounds is empty', () => {
    /**
     * **Validates: Requirements 3.1, 3.5**
     *
     * Edge case: with no other objects, no alignment guides should be detected.
     */
    fc.assert(
      fc.property(rectArb, thresholdArb, (dragged, threshold) => {
        const guides = detectAlignmentGuides(dragged, [], threshold);
        expect(guides).toHaveLength(0);
      }),
      { numRuns: 100 },
    );
  });
});
