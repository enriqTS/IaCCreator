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

// Feature: canvas-context-menu, Property 3: Send to back sets minimum zIndex
// **Validates: Requirements 2.4**
describe('Property 3: Send to back sets minimum zIndex', () => {
  beforeEach(resetStore);

  it('after sendToBack(id), target zIndex is strictly less than all other objects', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 2, maxLength: 8 }),
        fc.nat(),
        (objects, targetIndexRaw) => {
          resetStore();

          // Add objects to the store
          const ids: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            ids.push(id);
          }

          // Pick a random target
          const targetIndex = targetIndexRaw % ids.length;
          const targetId = ids[targetIndex];

          // Call sendToBack
          useDiagramStore.getState().sendToBack(targetId);

          const state = useDiagramStore.getState();
          const targetObj = state.canvasObjects.get(targetId)!;

          // Verify target zIndex is strictly less than all others
          for (const [id, obj] of state.canvasObjects) {
            if (id !== targetId) {
              expect(targetObj.zIndex).toBeLessThan(obj.zIndex);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
