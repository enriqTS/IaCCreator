import fc from 'fast-check';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock, LineObject } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_LINE_VISUAL, getObjectBounds } from '@/types/diagram';
import { getDefaultVariables } from '@/types/terraform-variables';

/**
 * Feature: canvas-objects-editor, Property 5: Anchored endpoint follows connected object
 * **Validates: Requirements 2.3**
 */
describe('Property 5: Anchored endpoint follows connected object', () => {
  beforeEach(() => {
    const state = useDiagramStore.getState();
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
        // Generate positions for two blocks and a move delta
        fc.record({
          posAx: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          posAy: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          posBx: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          posBy: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          dx: fc.double({ min: -500, max: 500, noNaN: true, noDefaultInfinity: true }),
          dy: fc.double({ min: -500, max: 500, noNaN: true, noDefaultInfinity: true }),
        }).filter(({ posAx, posAy, posBx, posBy, dx, dy }) => {
          // After moving block A, the line's end (at block B) must not coincide with block A's center.
          // Otherwise rayRectIntersection returns center (degenerate case with zero-length ray).
          const movedAx = posAx + dx;
          const movedAy = posAy + dy;
          const dist = Math.hypot(posBx - movedAx, posBy - movedAy);
          return dist > 1; // blocks must be at least 1px apart after move
        }),
        ({ posAx, posAy, posBx, posBy, dx, dy }) => {
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

          // Create a line anchored from A to B
          const lineId = store.addCanvasObject({
            objectType: 'line',
            name: 'Line1',
            start: { x: posAx, y: posAy },
            end: { x: posBx, y: posBy },
            sourceAnchor: { objectId: blockAId },
            targetAnchor: { objectId: blockBId },
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
