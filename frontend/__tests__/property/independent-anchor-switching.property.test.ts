/**
 * Property-based test: Independent anchor switching for source and target
 *
 * Feature: line-segment-manipulation, Property 11: Independent anchor switching for source and target
 *
 * **Validates: Requirements 4.5**
 *
 * For any line with both source and target anchors, updating the anchor position
 * on one end shall not modify the anchor position on the other end.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import type { AnchorPosition } from '@/utils/anchor';
import type { LineObject } from '@/types/diagram';

/** Arbitrary for an AnchorPosition. */
const anchorPositionArb: fc.Arbitrary<AnchorPosition> = fc.constantFrom(
  'top' as const,
  'right' as const,
  'bottom' as const,
  'left' as const,
);

/** Arbitrary for the endpoint to update. */
const endpointArb = fc.constantFrom('source' as const, 'target' as const);

function resetStore() {
  useDiagramStore.setState({
    connectors: new Map(),
    canvasObjects: new Map(),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

/**
 * Helper: create a line with both source and target anchors using the store.
 * Returns the line ID and the IDs of the two connected objects.
 */
function createAnchoredLine(
  sourceAnchorPos: AnchorPosition,
  targetAnchorPos: AnchorPosition,
): { lineId: string; sourceObjId: string; targetObjId: string } {
  const store = useDiagramStore.getState();

  const sourceObjId = store.addCanvasObject({
    objectType: 'geometric',
    name: 'source-obj',
    position: { x: 100, y: 100 },
    visualConfig: {
      width: 120, height: 80, fill: false,
      fillColor: '#3b82f6', borderColor: '#ffffff',
      borderWidth: 2, shape: 'rectangle',
    },
  });

  const targetObjId = store.addCanvasObject({
    objectType: 'geometric',
    name: 'target-obj',
    position: { x: 400, y: 300 },
    visualConfig: {
      width: 120, height: 80, fill: false,
      fillColor: '#3b82f6', borderColor: '#ffffff',
      borderWidth: 2, shape: 'rectangle',
    },
  });

  const lineId = store.addCanvasObject({
    objectType: 'line',
    name: 'test-line',
    start: { x: 160, y: 100 },
    end: { x: 340, y: 300 },
    sourceAnchor: { objectId: sourceObjId, anchorPosition: sourceAnchorPos },
    targetAnchor: { objectId: targetObjId, anchorPosition: targetAnchorPos },
    visualConfig: {
      color: '#ffffff', borderWidth: 2, strokeStyle: 'solid',
      startArrow: false, endArrow: false, routingMode: 'orthogonal',
    },
  });

  return { lineId, sourceObjId, targetObjId };
}

describe('Feature: line-segment-manipulation, Property 11: Independent anchor switching for source and target', () => {
  beforeEach(() => {
    resetStore();
  });

  it('updating source anchor position does not modify target anchor position', () => {
    /**
     * **Validates: Requirements 4.5**
     *
     * Strategy: Create a line with both anchors set to random positions.
     * Update the source anchor position to a new value. Verify the target
     * anchor position remains unchanged.
     */
    fc.assert(
      fc.property(
        anchorPositionArb,
        anchorPositionArb,
        anchorPositionArb,
        (initialSourcePos, initialTargetPos, newSourcePos) => {
          resetStore();
          const { lineId } = createAnchoredLine(initialSourcePos, initialTargetPos);

          // Update source anchor position
          useDiagramStore.getState().updateLineAnchorPosition(lineId, 'source', newSourcePos);

          const line = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
          expect(line.sourceAnchor!.anchorPosition).toBe(newSourcePos);
          expect(line.targetAnchor!.anchorPosition).toBe(initialTargetPos);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('updating target anchor position does not modify source anchor position', () => {
    /**
     * **Validates: Requirements 4.5**
     *
     * Strategy: Create a line with both anchors set to random positions.
     * Update the target anchor position to a new value. Verify the source
     * anchor position remains unchanged.
     */
    fc.assert(
      fc.property(
        anchorPositionArb,
        anchorPositionArb,
        anchorPositionArb,
        (initialSourcePos, initialTargetPos, newTargetPos) => {
          resetStore();
          const { lineId } = createAnchoredLine(initialSourcePos, initialTargetPos);

          // Update target anchor position
          useDiagramStore.getState().updateLineAnchorPosition(lineId, 'target', newTargetPos);

          const line = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
          expect(line.targetAnchor!.anchorPosition).toBe(newTargetPos);
          expect(line.sourceAnchor!.anchorPosition).toBe(initialSourcePos);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('updating either endpoint independently preserves the other across random sequences', () => {
    /**
     * **Validates: Requirements 4.5**
     *
     * Strategy: Create a line, then apply a random sequence of anchor position
     * updates to either source or target. After each update, verify the
     * non-updated end retains its previous position.
     */
    fc.assert(
      fc.property(
        anchorPositionArb,
        anchorPositionArb,
        fc.array(fc.tuple(endpointArb, anchorPositionArb), { minLength: 1, maxLength: 10 }),
        (initialSourcePos, initialTargetPos, updates) => {
          resetStore();
          const { lineId } = createAnchoredLine(initialSourcePos, initialTargetPos);

          let expectedSource = initialSourcePos;
          let expectedTarget = initialTargetPos;

          for (const [endpoint, newPos] of updates) {
            useDiagramStore.getState().updateLineAnchorPosition(lineId, endpoint, newPos);

            if (endpoint === 'source') {
              expectedSource = newPos;
            } else {
              expectedTarget = newPos;
            }

            const line = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
            expect(line.sourceAnchor!.anchorPosition).toBe(expectedSource);
            expect(line.targetAnchor!.anchorPosition).toBe(expectedTarget);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
