import fc from 'fast-check';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { LineObject } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_LINE_VISUAL } from '@/types/diagram';
import { getDefaultVariables } from '@/types/terraform-variables';

/**
 * Feature: canvas-objects-editor, Property 6: Anchor detach on object deletion
 * **Validates: Requirements 2.6**
 */
describe('Property 6: Anchor detach on object deletion', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
      connectors: new Map(),
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  it('deleting a referenced object nullifies the anchor but preserves the line and its positions', () => {
    fc.assert(
      fc.property(
        fc.record({
          blockX: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          blockY: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          lineStartX: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          lineStartY: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          lineEndX: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          lineEndY: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
        }),
        ({ blockX, blockY, lineStartX, lineStartY, lineEndX, lineEndY }) => {
          const store = useDiagramStore.getState();

          // Create an architecture block
          const blockId = store.addCanvasObject({
            objectType: 'architecture-block',
            serviceType: 'lambda',
            name: 'Block',
            position: { x: blockX, y: blockY },
            config: {},
            terraformVariables: getDefaultVariables('lambda'),
            visualConfig: { ...DEFAULT_BLOCK_VISUAL },
          });

          // Create a line with sourceAnchor referencing the block
          const lineId = store.addCanvasObject({
            objectType: 'line',
            name: 'Line',
            start: { x: lineStartX, y: lineStartY },
            end: { x: lineEndX, y: lineEndY },
            sourceAnchor: { objectId: blockId },
            targetAnchor: null,
            visualConfig: { ...DEFAULT_LINE_VISUAL },
          });

          // Capture the line's end position before deletion (start may be recomputed, end should stay)
          const lineBeforeDelete = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
          const endBefore = { ...lineBeforeDelete.end };
          const startBefore = { ...lineBeforeDelete.start };

          // Delete the block
          useDiagramStore.getState().removeCanvasObject(blockId);

          // Verify the block is gone
          expect(useDiagramStore.getState().canvasObjects.has(blockId)).toBe(false);

          // Verify the line still exists
          const lineAfterDelete = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
          expect(lineAfterDelete).toBeDefined();

          // Verify sourceAnchor is now null
          expect(lineAfterDelete.sourceAnchor).toBeNull();

          // Verify targetAnchor is still null (was never set)
          expect(lineAfterDelete.targetAnchor).toBeNull();

          // Verify start/end positions are preserved
          expect(lineAfterDelete.start.x).toBe(startBefore.x);
          expect(lineAfterDelete.start.y).toBe(startBefore.y);
          expect(lineAfterDelete.end.x).toBe(endBefore.x);
          expect(lineAfterDelete.end.y).toBe(endBefore.y);

          // Clean up for next iteration
          useDiagramStore.setState({
            canvasObjects: new Map(),
            selectedObjectIds: new Set(),
            objectGroups: new Map(),
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });
        }
      ),
      { numRuns: 100 }
    );
  });
});
