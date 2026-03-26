import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary } from './arbitraries';

function resetStore() {
  useDiagramStore.setState({
    canvasObjects: new Map(),
    connectors: new Map(),
    elements: new Map(),
    selectedObjectId: null,
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

// Feature: canvas-objects-editor, Property 9: Object deletion removes from store
// **Validates: Requirements 11.1, 11.2**
describe('Property 9: Object deletion removes from store', () => {
  beforeEach(resetStore);

  test('removing a canvas object by ID results in the store no longer containing that object', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        (objWithoutId) => {
          resetStore();

          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(objWithoutId);

          // Verify the object exists before deletion
          expect(useDiagramStore.getState().canvasObjects.has(id)).toBe(true);

          // Remove the object
          useDiagramStore.getState().removeCanvasObject(id);

          // Verify the object is gone
          const state = useDiagramStore.getState();
          expect(state.canvasObjects.has(id)).toBe(false);
          expect(state.canvasObjects.get(id)).toBeUndefined();
        }
      ),
      { numRuns: 100 }
    );
  });

  test('removing one object does not affect other objects in the store', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 2, maxLength: 10 }),
        fc.nat(),
        (objects, indexSeed) => {
          resetStore();

          // Add all objects
          const ids: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            ids.push(id);
          }

          // Pick one to remove
          const removeIndex = indexSeed % ids.length;
          const removedId = ids[removeIndex];
          const remainingIds = ids.filter((_, i) => i !== removeIndex);

          // Remove the chosen object
          useDiagramStore.getState().removeCanvasObject(removedId);

          const state = useDiagramStore.getState();

          // The removed object is gone
          expect(state.canvasObjects.has(removedId)).toBe(false);

          // All other objects still exist with correct objectType
          for (let i = 0; i < remainingIds.length; i++) {
            const remaining = state.canvasObjects.get(remainingIds[i]);
            expect(remaining).toBeDefined();
            // Map the remaining ID back to its original index
            const origIndex = ids.indexOf(remainingIds[i]);
            expect(remaining!.objectType).toBe(objects[origIndex].objectType);
          }

          // Total count is correct
          expect(state.canvasObjects.size).toBe(ids.length - 1);
        }
      ),
      { numRuns: 100 }
    );
  });
});
