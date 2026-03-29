import fc from 'fast-check';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock, LineObject } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_LINE_VISUAL, getObjectBounds } from '@/types/diagram';
import { getDefaultVariables } from '@/types/terraform-variables';
import { getAnchorPoints, type AnchorPosition } from '@/utils/anchor';

const anchorPositionArb = fc.constantFrom<AnchorPosition>('top', 'right', 'bottom', 'left');

/**
 * Feature: canvas-objects-editor, Property 5: Anchored endpoint follows connected object
 * **Validates: Requirements 2.3**
 */
describe('Property 5: Anchored endpoint follows connected object', () => {
  beforeEach(() => {
    // Reset store state
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
      elements: new Map(),
      connectors: new Map(),
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  it('after moving a connected block, the anchored line endpoint lies on the block boundary', () => {
    fc.assert(
      fc.property(
        // Generate positions for two blocks, a move delta, and anchor positions
        fc.record({
          posAx: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          posAy: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          posBx: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          posBy: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          dx: fc.double({ min: -500, max: 500, noNaN: true, noDefaultInfinity: true }),
          dy: fc.double({ min: -500, max: 500, noNaN: true, noDefaultInfinity: true }),
          sourceAnchorPos: anchorPositionArb,
          targetAnchorPos: anchorPositionArb,
        }),
        ({ posAx, posAy, posBx, posBy, dx, dy, sourceAnchorPos, targetAnchorPos }) => {
          const store = useDiagramStore.getState();

          // Create block A
          const blockAId = store.addCanvasObject({
            objectType: 'architecture-block',
            serviceType: 'lambda',
            name: 'BlockA',
            position: { x: posAx, y: posAy },
            config: {},
            terraformVariables: getDefaultVariables('lambda'),
            visualConfig: { ...DEFAULT_BLOCK_VISUAL },
          });

          // Create block B
          const blockBId = store.addCanvasObject({
            objectType: 'architecture-block',
            serviceType: 's3',
            name: 'BlockB',
            position: { x: posBx, y: posBy },
            config: {},
            terraformVariables: getDefaultVariables('s3'),
            visualConfig: { ...DEFAULT_BLOCK_VISUAL },
          });

          // Compute initial anchor coordinates
          const blockA = useDiagramStore.getState().canvasObjects.get(blockAId) as ArchitectureBlock;
          const blockB = useDiagramStore.getState().canvasObjects.get(blockBId) as ArchitectureBlock;
          const startPt = getAnchorPoints(getObjectBounds(blockA))[sourceAnchorPos];
          const endPt = getAnchorPoints(getObjectBounds(blockB))[targetAnchorPos];

          // Create a line anchored from A to B with fixed anchor positions
          const lineId = store.addCanvasObject({
            objectType: 'line',
            name: 'Line1',
            start: startPt,
            end: endPt,
            sourceAnchor: { objectId: blockAId, anchorPosition: sourceAnchorPos },
            targetAnchor: { objectId: blockBId, anchorPosition: targetAnchorPos },
            visualConfig: { ...DEFAULT_LINE_VISUAL },
          });

          // Select block A and move it
          useDiagramStore.getState().selectObject(blockAId);
          useDiagramStore.getState().moveSelectedObjects(dx, dy);

          // Get the updated line and block A
          const updatedLine = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
          const updatedBlockA = useDiagramStore.getState().canvasObjects.get(blockAId) as ArchitectureBlock;

          expect(updatedLine).toBeDefined();
          expect(updatedBlockA).toBeDefined();

          // The line's start point (anchored to block A) should lie on block A's boundary
          const boundsA = getObjectBounds(updatedBlockA);
          const eps = 1e-4;

          const left = boundsA.x;
          const right = boundsA.x + boundsA.width;
          const top = boundsA.y;
          const bottom = boundsA.y + boundsA.height;

          // Start point should be within block A's bounding box (on boundary)
          expect(updatedLine.start.x).toBeGreaterThanOrEqual(left - eps);
          expect(updatedLine.start.x).toBeLessThanOrEqual(right + eps);
          expect(updatedLine.start.y).toBeGreaterThanOrEqual(top - eps);
          expect(updatedLine.start.y).toBeLessThanOrEqual(bottom + eps);

          // At least one coordinate should be on an edge
          const onLeft = Math.abs(updatedLine.start.x - left) < eps;
          const onRight = Math.abs(updatedLine.start.x - right) < eps;
          const onTop = Math.abs(updatedLine.start.y - top) < eps;
          const onBottom = Math.abs(updatedLine.start.y - bottom) < eps;

          expect(onLeft || onRight || onTop || onBottom).toBe(true);

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
