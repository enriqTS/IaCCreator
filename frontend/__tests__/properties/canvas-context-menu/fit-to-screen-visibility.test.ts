import fc from 'fast-check';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import { getObjectBounds } from '@/types/diagram';
import type {
  CanvasObjectCreationPayload,
  Point,
} from '@/types/diagram';
import {
  DEFAULT_BLOCK_VISUAL,
  DEFAULT_LINE_VISUAL,
  DEFAULT_GEO_VISUAL,
} from '@/types/diagram';
import { getDefaultVariables } from '@/types/terraform-variables';
import { serviceTypeArbitrary } from '../arbitraries';

function resetStore() {
  useDiagramStore.setState({
    canvasObjects: new Map(),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    clipboard: [],
    elements: new Map(),
    connectors: new Map(),
    viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

/**
 * Generate objects with constrained positions so that the bounding box
 * fits within a reasonable range. This ensures the computed scale won't
 * be clamped to the 0.1 minimum, which would break the visibility guarantee.
 * 
 * With container min 200, padding 40, available = 120.
 * At scale 0.1, max canvas span = 1200. We constrain positions to ±400
 * so max span ~800 + object sizes ~120 = ~920, well within 1200.
 */
function constrainedPointArbitrary(): fc.Arbitrary<Point> {
  return fc.record({
    x: fc.double({ min: -400, max: 400, noNaN: true, noDefaultInfinity: true }),
    y: fc.double({ min: -400, max: 400, noNaN: true, noDefaultInfinity: true }),
  });
}

function constrainedCanvasObjectArbitrary(): fc.Arbitrary<CanvasObjectCreationPayload> {
  return fc.oneof(
    // architecture-block
    serviceTypeArbitrary().chain((st) =>
      fc.record({
        objectType: fc.constant('architecture-block' as const),
        serviceType: fc.constant(st),
        name: fc.string({ minLength: 1, maxLength: 10 }),
        position: constrainedPointArbitrary(),
        config: fc.constant({}),
        terraformVariables: fc.constant(getDefaultVariables(st)),
        visualConfig: fc.constant({ ...DEFAULT_BLOCK_VISUAL }),
      })
    ),
    // line
    fc.record({
      objectType: fc.constant('line' as const),
      name: fc.string({ minLength: 1, maxLength: 10 }),
      start: constrainedPointArbitrary(),
      end: constrainedPointArbitrary(),
      sourceAnchor: fc.constant(null),
      targetAnchor: fc.constant(null),
      visualConfig: fc.constant({ ...DEFAULT_LINE_VISUAL }),
    }),
    // geometric
    fc.record({
      objectType: fc.constant('geometric' as const),
      name: fc.string({ minLength: 1, maxLength: 10 }),
      position: constrainedPointArbitrary(),
      visualConfig: fc.constant({ ...DEFAULT_GEO_VISUAL }),
    }),
  );
}

// Feature: canvas-context-menu, Property 17: Fit to screen makes all objects visible
// **Validates: Requirements 9.3**
describe('Property 17: Fit to screen makes all objects visible', () => {
  beforeEach(resetStore);

  it('after fitToScreen, every object bounding box transformed through viewport falls within container bounds', () => {
    fc.assert(
      fc.property(
        fc.array(constrainedCanvasObjectArbitrary(), { minLength: 1, maxLength: 8 }),
        fc.record({
          width: fc.integer({ min: 200, max: 4000 }),
          height: fc.integer({ min: 200, max: 4000 }),
        }),
        (objects, containerRect) => {
          resetStore();

          // Add objects to the store
          for (const obj of objects) {
            useDiagramStore.getState().addCanvasObject(obj);
          }

          // Call fitToScreen
          useDiagramStore.getState().fitToScreen(containerRect);

          const state = useDiagramStore.getState();
          const { offsetX, offsetY, scale } = state.viewport;

          // Verify every object's screen-space bounding box is within container bounds
          for (const obj of state.canvasObjects.values()) {
            const bounds = getObjectBounds(obj);

            // Transform canvas-space bounds to screen-space via viewport:
            // screenX = canvasX * scale + offsetX
            const screenLeft = bounds.x * scale + offsetX;
            const screenTop = bounds.y * scale + offsetY;
            const screenRight = (bounds.x + bounds.width) * scale + offsetX;
            const screenBottom = (bounds.y + bounds.height) * scale + offsetY;

            // Small tolerance for floating point arithmetic
            const EPS = 1e-6;
            expect(screenLeft).toBeGreaterThanOrEqual(-EPS);
            expect(screenTop).toBeGreaterThanOrEqual(-EPS);
            expect(screenRight).toBeLessThanOrEqual(containerRect.width + EPS);
            expect(screenBottom).toBeLessThanOrEqual(containerRect.height + EPS);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
