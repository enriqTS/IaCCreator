/**
 * Bug Condition Exploration Tests
 *
 * These tests demonstrate the 4 bugs exist in the current (unfixed) code.
 * They are EXPECTED TO FAIL on unfixed code, confirming the bugs.
 */

import { describe, it, expect } from 'vitest';
import { computeShapeEdgePoint } from '@/utils/bounds-utils';
import type { GeometricObject, LineObject, Rect } from '@/types/diagram';

/**
 * Bug 1: Line targeting a circle terminates at bounding-box cardinal midpoints
 * instead of the actual circle perimeter.
 *
 * **Validates: Requirements 2.1**
 */
describe('Bug 1: Circle line termination at shape boundary', () => {
  it('anchor point for circle should lie on circle perimeter, not AABB midpoint', () => {
    // Create a circle geometric object centered at (200, 200) with radius 60
    const circleObj: GeometricObject = {
      id: 'circle-1',
      objectType: 'geometric',
      name: 'Circle',
      position: { x: 200, y: 200 },
      visualConfig: {
        width: 120,
        height: 120,
        fill: false,
        fillColor: '#3b82f6',
        borderColor: '#ffffff',
        borderWidth: 2,
        shape: 'circle',
      },
      zIndex: 0,
    };

    const cx = 200;
    const cy = 200;
    const radius = 60;

    // Test with an external point at 45 degrees (top-right)
    const externalPoint = { x: 300, y: 100 };
    const edgePoint = computeShapeEdgePoint(circleObj, externalPoint);

    // The edge point should lie exactly on the circle perimeter
    const distToCenter = Math.sqrt(
      (edgePoint.x - cx) ** 2 + (edgePoint.y - cy) ** 2
    );

    // Distance from center to the computed edge point should equal radius
    expect(distToCenter).toBeCloseTo(radius, 0);
  });
});

/**
 * Bug 2: Switching routing mode from orthogonal to diagonal causes React hooks crash.
 *
 * The `diagShortened` useMemo in LineObjectComponent is placed AFTER the
 * conditional return for orthogonal mode, violating React's Rules of Hooks.
 *
 * **Validates: Requirements 2.2**
 */
describe('Bug 2: Routing mode switch hooks violation', () => {
  it('LineObjectComponent should not crash when switching from orthogonal to diagonal', async () => {
    // We test by importing the component and checking that the useMemo (diagShortened)
    // is defined after the conditional return. This is a static analysis check.
    const fs = await import('fs');
    const path = await import('path');
    const componentPath = path.resolve(__dirname, '../../../src/components/canvas/objects/LineObjectComponent.tsx');
    const source = fs.readFileSync(componentPath, 'utf-8');

    // Find the positions of the orthogonal conditional return and diagShortened useMemo
    const orthogonalReturnIndex = source.indexOf('if (useOrthogonal) {');
    const diagShortenedIndex = source.indexOf('const diagShortened = useMemo(');

    // The bug: diagShortened useMemo is AFTER the orthogonal conditional return.
    // This means when switching from orthogonal (early return, fewer hooks) to
    // diagonal (no early return, more hooks), React sees a different hook count.
    // For correctness, diagShortened should be BEFORE the conditional return.
    expect(diagShortenedIndex).toBeLessThan(orthogonalReturnIndex);
  });
});

/**
 * Bug 3: Arrow placement fails because isCanvasBackground check is too restrictive.
 *
 * When place-arrow is active, mousedown on a non-background element (like the
 * viewport-transform-container div) doesn't initiate arrow drag because the
 * isCanvasBackground check fails.
 *
 * **Validates: Requirements 2.3**
 */
describe('Bug 3: Arrow placement blocked by isCanvasBackground check', () => {
  it('place-arrow handler should be reachable regardless of event target', async () => {
    // Read the Canvas source to verify the place-arrow handling is gated behind isCanvasBackground
    const fs = await import('fs');
    const path = await import('path');
    const canvasPath = path.resolve(__dirname, '../../../src/components/canvas/Canvas.tsx');
    const source = fs.readFileSync(canvasPath, 'utf-8');

    // Find the handleMouseDown function
    const handleMouseDownStart = source.indexOf('const handleMouseDown = useCallback(');
    const handleMouseDownBody = source.slice(handleMouseDownStart, handleMouseDownStart + 3000);

    // Find the isCanvasBackground check
    const bgCheckIndex = handleMouseDownBody.indexOf('if (e.button === 0 && isCanvasBackground)');

    // Find the place-arrow handling
    const placeArrowIndex = handleMouseDownBody.indexOf("activeTool.type === 'place-arrow'");

    // Bug: place-arrow handling is INSIDE the isCanvasBackground block,
    // meaning it only fires when the click target is the canvas background itself.
    // It should work regardless of target element (like place-service uses DragSizingOverlay).
    // For the fix, place-arrow should be handled BEFORE or OUTSIDE the isCanvasBackground gate.
    expect(placeArrowIndex).toBeLessThan(bgCheckIndex);
  });
});

/**
 * Bug 4: Service placed via DragSizingOverlay gets hardcoded name "Service"
 * instead of auto-generated name.
 *
 * **Validates: Requirements 2.4**
 */
describe('Bug 4: Hardcoded service name overrides auto-generated default', () => {
  it('handlePlaceObject should NOT pass hardcoded name for place-service', async () => {
    // Read the Canvas source to verify the place-service branch passes name: 'Service'
    const fs = await import('fs');
    const path = await import('path');
    const canvasPath = path.resolve(__dirname, '../../../src/components/canvas/Canvas.tsx');
    const source = fs.readFileSync(canvasPath, 'utf-8');

    // Find the handlePlaceObject callback
    const handlePlaceObjectStart = source.indexOf('const handlePlaceObject = useCallback(');
    const handlePlaceObjectBody = source.slice(handlePlaceObjectStart, handlePlaceObjectStart + 2000);

    // Find place-service branch
    const placeServiceBranch = handlePlaceObjectBody.indexOf("tool.type === 'place-service'");
    const branchBody = handlePlaceObjectBody.slice(placeServiceBranch, placeServiceBranch + 800);

    // Bug: The branch includes `name: 'Service'` in the addCanvasObject payload.
    // Since 'Service' is truthy, the store's `assignedName = obj.name || defaultName`
    // always uses 'Service' instead of the auto-generated name from generateDefaultName.
    // The fix: do NOT pass a `name` field, letting addCanvasObject use generateDefaultName.
    const hasHardcodedName = branchBody.includes("name: 'Service'");
    expect(hasHardcodedName).toBe(false);
  });
});
