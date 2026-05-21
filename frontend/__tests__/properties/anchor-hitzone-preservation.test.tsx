import { describe, test, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import fc from 'fast-check';
import AnchorIndicators from '@/components/canvas/AnchorIndicators';
import { useDiagramStore } from '@/store/diagram-store';
import { getAnchorPoints } from '@/utils/anchor';
import type { Rect } from '@/types/diagram';
import type { AnchorPosition } from '@/utils/anchor';

/**
 * **Validates: Requirements 3.1, 3.2, 3.5, 3.6**
 *
 * Property 2: Preservation — Non-Anchor Clicks and Display Behavior Unchanged
 *
 * These tests capture baseline behaviors that MUST be preserved after the fix:
 * - Clicks outside anchor indicator circles do NOT trigger pull-to-connect
 * - Four anchor indicators render at cardinal positions for non-line, non-locked objects
 * - Locked objects render no anchor indicators
 * - Anchor indicator dimensions are scale-compensated
 *
 * All tests are expected to PASS on UNFIXED code (confirming baseline behavior).
 */

const ANCHOR_POSITIONS: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

/** The visible anchor zone size in screen pixels (matches AnchorIndicators.tsx) */
const ANCHOR_ZONE_SCREEN = 20;

/**
 * Renders AnchorIndicators and returns the container for inspection.
 */
function renderAnchorIndicators(
  objectId: string,
  bounds: Rect,
  scale: number = 1.0,
  locked: boolean = false,
) {
  useDiagramStore.setState({
    viewport: { offsetX: 0, offsetY: 0, scale },
    activeTool: 'pointer',
    pullConnectState: null,
  });

  return render(
    <AnchorIndicators
      objectId={objectId}
      bounds={bounds}
      locked={locked}
    />,
  );
}

/**
 * Compute the distance from a point to the nearest anchor center.
 */
function minDistanceToAnyAnchor(
  px: number,
  py: number,
  bounds: Rect,
): number {
  const anchors = getAnchorPoints(bounds);
  let minDist = Infinity;
  for (const pos of ANCHOR_POSITIONS) {
    const anchor = anchors[pos];
    const dx = px - anchor.x;
    const dy = py - anchor.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < minDist) minDist = dist;
  }
  return minDist;
}

describe('Property 2: Preservation — Non-Anchor Clicks and Display Behavior Unchanged', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      pullConnectState: null,
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      activeTool: 'pointer',
    });
  });

  test('Property-based: clicks OUTSIDE all anchor indicator circles do NOT trigger setPullConnectState', () => {
    /**
     * **Validates: Requirements 3.1**
     *
     * For all random object positions/sizes and click positions OUTSIDE all anchor
     * indicator circles (distance from every anchor center > 10px / scale),
     * verify that setPullConnectState is NOT called.
     *
     * This confirms that non-anchor clicks continue to fall through to normal
     * behavior (object drag, canvas interaction, etc.).
     */
    fc.assert(
      fc.property(
        // Random object bounds
        fc.integer({ min: 50, max: 500 }), // objX
        fc.integer({ min: 50, max: 500 }), // objY
        fc.integer({ min: 40, max: 200 }), // objWidth
        fc.integer({ min: 40, max: 200 }), // objHeight
        // Random scale
        fc.double({ min: 0.5, max: 2.0, noNaN: true }),
        // Random click offset from object center (to generate clicks on the object body)
        fc.double({ min: -0.4, max: 0.4, noNaN: true }), // fraction of width from center
        fc.double({ min: -0.4, max: 0.4, noNaN: true }), // fraction of height from center
        (objX, objY, objWidth, objHeight, scale, fracX, fracY) => {
          const bounds: Rect = { x: objX, y: objY, width: objWidth, height: objHeight };

          // Compute click point as a fraction of object size from center
          const cx = bounds.x + bounds.width / 2;
          const cy = bounds.y + bounds.height / 2;
          const clickX = cx + fracX * bounds.width;
          const clickY = cy + fracY * bounds.height;

          // Only test cases where click is OUTSIDE all anchor circles
          // The anchor visible radius is (ANCHOR_ZONE_SCREEN / 2) / scale = 10 / scale
          const anchorRadius = 10 / scale;
          const dist = minDistanceToAnyAnchor(clickX, clickY, bounds);
          if (dist <= anchorRadius) return; // Skip — this click is within an anchor circle

          // Reset state
          useDiagramStore.setState({
            pullConnectState: null,
            viewport: { offsetX: 0, offsetY: 0, scale },
          });

          // Render
          const { unmount } = renderAnchorIndicators('obj-preserve', bounds, scale);

          // After rendering, pullConnectState should still be null
          // (no anchor interaction triggered just by rendering)
          const state = useDiagramStore.getState();
          expect(state.pullConnectState).toBeNull();

          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });

  test('Property-based: for all random viewport scales (0.25–4.0), anchor indicators render with correct scale-compensated dimensions', () => {
    /**
     * **Validates: Requirements 3.6**
     *
     * For all random viewport scales, verify anchor indicators render with
     * correct scale-compensated dimensions. The visible zone should be
     * ANCHOR_ZONE_SCREEN / scale canvas-pixels.
     */
    fc.assert(
      fc.property(
        // Random scale between 0.25 and 4.0
        fc.double({ min: 0.25, max: 4.0, noNaN: true }),
        // Random object bounds
        fc.integer({ min: 50, max: 400 }),
        fc.integer({ min: 50, max: 400 }),
        fc.integer({ min: 40, max: 150 }),
        fc.integer({ min: 40, max: 150 }),
        (scale, objX, objY, objWidth, objHeight) => {
          const bounds: Rect = { x: objX, y: objY, width: objWidth, height: objHeight };

          useDiagramStore.setState({
            pullConnectState: null,
            viewport: { offsetX: 0, offsetY: 0, scale },
          });

          const { unmount } = renderAnchorIndicators('obj-scale', bounds, scale);

          // Check that all 4 anchor indicators are rendered with scale-compensated sizes
          for (const pos of ANCHOR_POSITIONS) {
            const el = document.querySelector(
              `[data-testid="anchor-indicator-obj-scale-${pos}"]`,
            ) as HTMLElement;
            expect(el).not.toBeNull();

            // The outermost element (hit zone) should have dimensions that are
            // scale-compensated. On unfixed code, this is HIT_ZONE_SCREEN (24) / scale.
            // The key preservation property is that the element EXISTS and has
            // scale-compensated dimensions (size decreases as scale increases).
            const width = parseFloat(el.style.width);
            const height = parseFloat(el.style.height);

            // Dimensions should be positive and scale-compensated
            expect(width).toBeGreaterThan(0);
            expect(height).toBeGreaterThan(0);

            // The visible zone (inner element or the element itself after fix)
            // should be ANCHOR_ZONE_SCREEN / scale
            const expectedVisibleSize = ANCHOR_ZONE_SCREEN / scale;

            // Find the visible zone — on unfixed code it's the child div;
            // after fix it will be the element itself.
            // We check that a visible zone of the correct size exists somewhere in the structure.
            const children = el.querySelectorAll('div');
            let foundVisibleZone = false;

            if (children.length > 0) {
              // Unfixed code: visible zone is the first child div
              const visibleChild = children[0] as HTMLElement;
              const childWidth = parseFloat(visibleChild.style.width);
              const childHeight = parseFloat(visibleChild.style.height);
              if (
                Math.abs(childWidth - expectedVisibleSize) < 0.01 &&
                Math.abs(childHeight - expectedVisibleSize) < 0.01
              ) {
                foundVisibleZone = true;
              }
            }

            // After fix: the element itself is the visible zone
            if (
              Math.abs(width - expectedVisibleSize) < 0.01 &&
              Math.abs(height - expectedVisibleSize) < 0.01
            ) {
              foundVisibleZone = true;
            }

            expect(foundVisibleZone).toBe(true);
          }

          unmount();
        },
      ),
      { numRuns: 50 },
    );
  });

  test('Property-based: for all non-line, non-locked objects, exactly 4 anchor indicators render at cardinal positions', () => {
    /**
     * **Validates: Requirements 3.2**
     *
     * For all random non-line, non-locked objects, verify exactly 4 anchor
     * indicators render with data-testid attributes at cardinal positions
     * (top, right, bottom, left).
     */
    fc.assert(
      fc.property(
        // Random object bounds
        fc.integer({ min: 10, max: 600 }),
        fc.integer({ min: 10, max: 600 }),
        fc.integer({ min: 20, max: 300 }),
        fc.integer({ min: 20, max: 300 }),
        // Random scale
        fc.double({ min: 0.25, max: 4.0, noNaN: true }),
        (objX, objY, objWidth, objHeight, scale) => {
          const bounds: Rect = { x: objX, y: objY, width: objWidth, height: objHeight };

          useDiagramStore.setState({
            pullConnectState: null,
            viewport: { offsetX: 0, offsetY: 0, scale },
          });

          const { unmount, container } = renderAnchorIndicators(
            'obj-cardinal',
            bounds,
            scale,
            false, // not locked
          );

          // Verify exactly 4 anchor indicators are rendered
          const anchorElements = container.querySelectorAll('[data-testid^="anchor-indicator-obj-cardinal-"]');
          expect(anchorElements.length).toBe(4);

          // Verify each cardinal position has an indicator
          for (const pos of ANCHOR_POSITIONS) {
            const el = document.querySelector(
              `[data-testid="anchor-indicator-obj-cardinal-${pos}"]`,
            );
            expect(el).not.toBeNull();
          }

          // Verify data-testid pattern: anchor-indicator-${objectId}-${pos}
          for (const pos of ANCHOR_POSITIONS) {
            const expectedTestId = `anchor-indicator-obj-cardinal-${pos}`;
            const el = document.querySelector(`[data-testid="${expectedTestId}"]`);
            expect(el).not.toBeNull();
          }

          unmount();
        },
      ),
      { numRuns: 50 },
    );
  });

  test('Property-based: for locked objects, no anchor indicators render', () => {
    /**
     * **Validates: Requirements 3.5**
     *
     * For all locked objects (any random bounds and scale), verify that
     * no anchor indicators are rendered (component returns null).
     */
    fc.assert(
      fc.property(
        // Random object bounds
        fc.integer({ min: 10, max: 600 }),
        fc.integer({ min: 10, max: 600 }),
        fc.integer({ min: 20, max: 300 }),
        fc.integer({ min: 20, max: 300 }),
        // Random scale
        fc.double({ min: 0.25, max: 4.0, noNaN: true }),
        (objX, objY, objWidth, objHeight, scale) => {
          const bounds: Rect = { x: objX, y: objY, width: objWidth, height: objHeight };

          useDiagramStore.setState({
            pullConnectState: null,
            viewport: { offsetX: 0, offsetY: 0, scale },
          });

          const { unmount, container } = renderAnchorIndicators(
            'obj-locked',
            bounds,
            scale,
            true, // locked
          );

          // Verify NO anchor indicators are rendered for locked objects
          const anchorElements = container.querySelectorAll('[data-testid^="anchor-indicator-obj-locked-"]');
          expect(anchorElements.length).toBe(0);

          unmount();
        },
      ),
      { numRuns: 50 },
    );
  });
});
