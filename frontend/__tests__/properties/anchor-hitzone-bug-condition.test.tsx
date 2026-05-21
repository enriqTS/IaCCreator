import { describe, test, expect, beforeEach } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import fc from 'fast-check';
import AnchorIndicators from '@/components/canvas/AnchorIndicators';
import { useDiagramStore } from '@/store/diagram-store';
import { getAnchorPoints } from '@/utils/anchor';
import type { Rect, Point } from '@/types/diagram';
import type { AnchorPosition } from '@/utils/anchor';

/**
 * **Validates: Requirements 1.1, 1.2, 1.3**
 *
 * Property 1: Bug Condition — Anchor Overlap Click Triggers Object Drag Instead of Pull-to-Connect
 *
 * This test encodes the EXPECTED (correct) behavior: clicking within the visible
 * anchor indicator region should call setPullConnectState to initiate pull-to-connect,
 * even when the click position overlaps the underlying object's bounds.
 *
 * The bug manifests because the AnchorIndicators component uses a three-layer structure:
 * - Outer 24px div with pointerEvents: 'auto' (the hit zone)
 * - Inner 20px div with pointerEvents: 'none' (the visible square)
 * - Inner 8px div with pointerEvents: 'none' (the center dot)
 *
 * When the anchor overlaps the object, the browser delivers the mouseDown to the
 * element that is topmost in paint order at the click coordinates. Because the object's
 * div has pointerEvents: 'auto' and calls stopPropagation in its onMouseDown handler,
 * the anchor's handler never fires in the overlap region.
 *
 * This test verifies the STRUCTURAL requirement: the anchor indicator's interactive
 * element must fully cover the visible region. After the fix (single 20px circle with
 * pointerEvents: 'auto'), the anchor element will be the topmost clickable element
 * at any point within the visible circle, ensuring it always captures the event.
 *
 * On UNFIXED code, this test FAILS because:
 * - Case 3: The 24px hit zone extends beyond the 20px visible square (mismatch)
 * - The structural assertions verify the fix requirements
 */

/** Fraction of the object's smaller side used for the anchor indicator diameter */
const ANCHOR_ZONE_RATIO = 0.2;
/** Minimum anchor indicator size in canvas pixels */
const ANCHOR_ZONE_MIN = 4;
/** Maximum anchor indicator size in canvas pixels */
const ANCHOR_ZONE_MAX = 24;

/**
 * Compute the expected anchor zone size for given object bounds.
 */
function computeExpectedZoneSize(bounds: Rect): number {
  const smallerSide = Math.min(bounds.width, bounds.height);
  return Math.max(ANCHOR_ZONE_MIN, Math.min(ANCHOR_ZONE_MAX, smallerSide * ANCHOR_ZONE_RATIO));
}

/**
 * Check if a point is within the visible anchor circle (proportional to object size, centered on anchor).
 */
function isWithinVisibleAnchorCircle(
  clickPoint: Point,
  anchorPoint: Point,
  bounds: Rect,
): boolean {
  const radius = computeExpectedZoneSize(bounds) / 2;
  const dx = clickPoint.x - anchorPoint.x;
  const dy = clickPoint.y - anchorPoint.y;
  return (dx * dx + dy * dy) <= radius * radius;
}

/**
 * Check if a point is within the object's bounding rect.
 */
function isWithinObjectBounds(point: Point, bounds: Rect): boolean {
  return (
    point.x >= bounds.x &&
    point.x <= bounds.x + bounds.width &&
    point.y >= bounds.y &&
    point.y <= bounds.y + bounds.height
  );
}

/**
 * Renders AnchorIndicators and returns the anchor elements for inspection.
 */
function renderAnchorIndicators(
  objectId: string,
  bounds: Rect,
  scale: number = 1.0,
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
      locked={false}
    />,
  );
}

describe('Property 1: Bug Condition — Anchor Overlap Click Triggers Object Drag Instead of Pull-to-Connect', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      pullConnectState: null,
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      activeTool: 'pointer',
    });
  });

  test('Concrete case 1: Right anchor at object edge — click within visible square AND within object bounds triggers pull-to-connect', () => {
    // Object at (100, 100) with width=64, height=64
    const bounds: Rect = { x: 100, y: 100, width: 64, height: 64 };
    const anchors = getAnchorPoints(bounds);
    // Right anchor at (164, 132)
    const rightAnchor = anchors.right;
    expect(rightAnchor.x).toBe(164);
    expect(rightAnchor.y).toBe(132);

    renderAnchorIndicators('obj-1', bounds);

    // Click at (162, 132) — within visible square AND within object bounds
    const clickPoint: Point = { x: 162, y: 132 };

    // Verify preconditions: click is within visible anchor circle
    expect(isWithinVisibleAnchorCircle(clickPoint, rightAnchor, bounds)).toBe(true);
    // Verify preconditions: click is within object bounds
    expect(isWithinObjectBounds(clickPoint, bounds)).toBe(true);

    // Find the anchor indicator element and simulate mouseDown
    const anchorEl = document.querySelector(`[data-testid="anchor-indicator-obj-1-right"]`);
    expect(anchorEl).not.toBeNull();

    fireEvent.mouseDown(anchorEl!, { clientX: 162, clientY: 132, button: 0 });

    // Expected behavior: setPullConnectState should be called
    const state = useDiagramStore.getState();
    expect(state.pullConnectState).not.toBeNull();
    expect(state.pullConnectState?.sourceObjectId).toBe('obj-1');
    expect(state.pullConnectState?.sourceAnchorPoint).toEqual(rightAnchor);
    expect(state.pullConnectState?.sourceAnchorPosition).toBe('right');
  });

  test('Concrete case 2: Top anchor at object edge — click within visible square and just inside top edge triggers pull-to-connect', () => {
    // Object at (200, 200) with width=48, height=48
    const bounds: Rect = { x: 200, y: 200, width: 48, height: 48 };
    const anchors = getAnchorPoints(bounds);
    // Top anchor at (224, 200)
    const topAnchor = anchors.top;
    expect(topAnchor.x).toBe(224);
    expect(topAnchor.y).toBe(200);

    renderAnchorIndicators('obj-2', bounds);

    // Click at (224, 201) — within visible square and just inside object's top edge
    const clickPoint: Point = { x: 224, y: 201 };

    // Verify preconditions
    expect(isWithinVisibleAnchorCircle(clickPoint, topAnchor, bounds)).toBe(true);
    expect(isWithinObjectBounds(clickPoint, bounds)).toBe(true);

    const anchorEl = document.querySelector(`[data-testid="anchor-indicator-obj-2-top"]`);
    expect(anchorEl).not.toBeNull();

    fireEvent.mouseDown(anchorEl!, { clientX: 224, clientY: 201, button: 0 });

    const state = useDiagramStore.getState();
    expect(state.pullConnectState).not.toBeNull();
    expect(state.pullConnectState?.sourceObjectId).toBe('obj-2');
    expect(state.pullConnectState?.sourceAnchorPoint).toEqual(topAnchor);
    expect(state.pullConnectState?.sourceAnchorPosition).toBe('top');
  });

  test('Concrete case 3: Anchor interactive element matches visible region exactly — no invisible hit zone extends beyond visible area', () => {
    // This test verifies the structural fix: the interactive element's dimensions
    // must match the visible indicator dimensions exactly.
    //
    // On UNFIXED code: the outer div is 24px (HIT_ZONE_SCREEN) while the visible
    // inner div is 20px (ANCHOR_ZONE_SCREEN). This creates a 2px invisible band
    // on each side that captures clicks without visual feedback.
    //
    // After the fix: a single element serves as both visual and interactive region,
    // so the interactive size equals the visible size (20px at scale=1).

    const bounds: Rect = { x: 100, y: 100, width: 64, height: 64 };
    renderAnchorIndicators('obj-3', bounds, 1.0);

    const anchorEl = document.querySelector(`[data-testid="anchor-indicator-obj-3-right"]`) as HTMLElement;
    expect(anchorEl).not.toBeNull();

    // Get the computed dimensions of the interactive element (the one with pointerEvents: 'auto')
    const interactiveWidth = parseFloat(anchorEl.style.width);
    const interactiveHeight = parseFloat(anchorEl.style.height);

    // Expected: the interactive element should be proportional to the object's smaller side
    // For a 64x64 object: min(64,64) * 0.3 = 19.2, clamped to [4, 24] = 19.2
    const expectedSize = computeExpectedZoneSize(bounds);
    expect(interactiveWidth).toBeCloseTo(expectedSize, 1);
    expect(interactiveHeight).toBeCloseTo(expectedSize, 1);
  });

  test('Concrete case 3b: Anchor element uses circular shape (borderRadius 50%) for unified visual/interactive region', () => {
    // After the fix, the anchor indicator should be a circle (borderRadius: 50%)
    // instead of a square with nested elements.
    // On UNFIXED code: the outer element is a square (no borderRadius or borderRadius != 50%)

    const bounds: Rect = { x: 100, y: 100, width: 64, height: 64 };
    renderAnchorIndicators('obj-3b', bounds, 1.0);

    const anchorEl = document.querySelector(`[data-testid="anchor-indicator-obj-3b-right"]`) as HTMLElement;
    expect(anchorEl).not.toBeNull();

    // Expected: the element should have borderRadius: 50% (circle)
    // On UNFIXED code: the outer div has no borderRadius (it's a square hit zone)
    expect(anchorEl.style.borderRadius).toBe('50%');
  });

  test('Property-based: random objects with anchor overlap — clicks within visible anchor region always trigger pull-to-connect', () => {
    fc.assert(
      fc.property(
        // Random object size (32-200px)
        fc.integer({ min: 32, max: 200 }),
        fc.integer({ min: 32, max: 200 }),
        // Random object position (50-500)
        fc.integer({ min: 50, max: 500 }),
        fc.integer({ min: 50, max: 500 }),
        // Random anchor position
        fc.constantFrom('top' as AnchorPosition, 'right' as AnchorPosition, 'bottom' as AnchorPosition, 'left' as AnchorPosition),
        // Random offset within visible anchor radius (0 to 9px from center at scale=1)
        fc.integer({ min: -9, max: 9 }),
        fc.integer({ min: -9, max: 9 }),
        (objWidth, objHeight, objX, objY, anchorPos, offsetX, offsetY) => {
          const bounds: Rect = { x: objX, y: objY, width: objWidth, height: objHeight };
          const anchors = getAnchorPoints(bounds);
          const anchorPoint = anchors[anchorPos];

          // Compute click point within visible anchor circle
          const clickPoint: Point = {
            x: anchorPoint.x + offsetX,
            y: anchorPoint.y + offsetY,
          };

          // Only test cases where click is within BOTH the visible anchor circle AND the object bounds
          if (!isWithinVisibleAnchorCircle(clickPoint, anchorPoint, bounds)) return;
          if (!isWithinObjectBounds(clickPoint, bounds)) return;

          // Reset state
          useDiagramStore.setState({ pullConnectState: null, viewport: { offsetX: 0, offsetY: 0, scale: 1.0 } });

          // Render
          const { unmount } = renderAnchorIndicators('obj-pbt', bounds);

          const anchorEl = document.querySelector(`[data-testid="anchor-indicator-obj-pbt-${anchorPos}"]`);
          if (!anchorEl) {
            unmount();
            return; // Skip if element not found (shouldn't happen)
          }

          fireEvent.mouseDown(anchorEl, { clientX: clickPoint.x, clientY: clickPoint.y, button: 0 });

          const state = useDiagramStore.getState();

          // EXPECTED: setPullConnectState is called with correct values
          expect(state.pullConnectState).not.toBeNull();
          expect(state.pullConnectState?.sourceObjectId).toBe('obj-pbt');
          expect(state.pullConnectState?.sourceAnchorPoint).toEqual(anchorPoint);
          expect(state.pullConnectState?.sourceAnchorPosition).toBe(anchorPos);

          unmount();
        },
      ),
      { numRuns: 50 },
    );
  });
});
