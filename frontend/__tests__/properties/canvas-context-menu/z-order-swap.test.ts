import fc from 'fast-check';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary } from '../arbitraries';

function resetStore() {
  useDiagramStore.setState({
    canvasObjects: new Map(),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    clipboard: [],
    connectors: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

// Feature: canvas-context-menu, Property 4: Bring forward / send backward swap adjacent z-orders
// **Validates: Requirements 2.2, 2.3**
describe('Property 4: Bring forward / send backward swap adjacent z-orders', () => {
  beforeEach(resetStore);

  it('bringForward swaps zIndex with the object directly above, others unchanged', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 2, maxLength: 8 }),
        fc.nat(),
        (objects, targetIndexRaw) => {
          resetStore();

          const ids: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            ids.push(id);
          }

          const targetIndex = targetIndexRaw % ids.length;
          const targetId = ids[targetIndex];

          // Snapshot zIndex values before
          const state = useDiagramStore.getState();
          const zBefore = new Map<string, number>();
          for (const [id, obj] of state.canvasObjects) {
            zBefore.set(id, obj.zIndex);
          }

          const targetZBefore = zBefore.get(targetId)!;

          // Find the object directly above (smallest zIndex > target's)
          let aboveId: string | null = null;
          let aboveZ = Infinity;
          for (const [id, z] of zBefore) {
            if (id !== targetId && z > targetZBefore && z < aboveZ) {
              aboveZ = z;
              aboveId = id;
            }
          }

          // Call bringForward
          useDiagramStore.getState().bringForward(targetId);

          const after = useDiagramStore.getState();

          if (aboveId === null) {
            // Target was already at top — nothing should change
            for (const [id, obj] of after.canvasObjects) {
              expect(obj.zIndex).toBe(zBefore.get(id)!);
            }
          } else {
            // Target and above should have swapped
            const targetAfter = after.canvasObjects.get(targetId)!;
            const aboveAfter = after.canvasObjects.get(aboveId)!;

            expect(targetAfter.zIndex).toBe(aboveZ);
            expect(aboveAfter.zIndex).toBe(targetZBefore);

            // All other objects unchanged
            for (const [id, obj] of after.canvasObjects) {
              if (id !== targetId && id !== aboveId) {
                expect(obj.zIndex).toBe(zBefore.get(id)!);
              }
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('sendBackward swaps zIndex with the object directly below, others unchanged', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 2, maxLength: 8 }),
        fc.nat(),
        (objects, targetIndexRaw) => {
          resetStore();

          const ids: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            ids.push(id);
          }

          const targetIndex = targetIndexRaw % ids.length;
          const targetId = ids[targetIndex];

          // Snapshot zIndex values before
          const state = useDiagramStore.getState();
          const zBefore = new Map<string, number>();
          for (const [id, obj] of state.canvasObjects) {
            zBefore.set(id, obj.zIndex);
          }

          const targetZBefore = zBefore.get(targetId)!;

          // Find the object directly below (largest zIndex < target's)
          let belowId: string | null = null;
          let belowZ = -Infinity;
          for (const [id, z] of zBefore) {
            if (id !== targetId && z < targetZBefore && z > belowZ) {
              belowZ = z;
              belowId = id;
            }
          }

          // Call sendBackward
          useDiagramStore.getState().sendBackward(targetId);

          const after = useDiagramStore.getState();

          if (belowId === null) {
            // Target was already at bottom — nothing should change
            for (const [id, obj] of after.canvasObjects) {
              expect(obj.zIndex).toBe(zBefore.get(id)!);
            }
          } else {
            // Target and below should have swapped
            const targetAfter = after.canvasObjects.get(targetId)!;
            const belowAfter = after.canvasObjects.get(belowId)!;

            expect(targetAfter.zIndex).toBe(belowZ);
            expect(belowAfter.zIndex).toBe(targetZBefore);

            // All other objects unchanged
            for (const [id, obj] of after.canvasObjects) {
              if (id !== targetId && id !== belowId) {
                expect(obj.zIndex).toBe(zBefore.get(id)!);
              }
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
