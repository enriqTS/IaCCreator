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

// Feature: canvas-context-menu, Property 2: Bring to front sets maximum zIndex
// **Validates: Requirements 2.1**
describe('Property 2: Bring to front sets maximum zIndex', () => {
  beforeEach(resetStore);

  it('after bringToFront(id), target zIndex is strictly greater than all other objects', () => {
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

          // Call bringToFront
          useDiagramStore.getState().bringToFront(targetId);

          const state = useDiagramStore.getState();
          const targetObj = state.canvasObjects.get(targetId)!;

          // Verify target zIndex is strictly greater than all others
          for (const [id, obj] of state.canvasObjects) {
            if (id !== targetId) {
              expect(targetObj.zIndex).toBeGreaterThan(obj.zIndex);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
