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

// Feature: canvas-objects-editor, Property 11: Deletion clears selection
// **Validates: Requirements 11.4**
describe('Property 11: Deletion clears selection', () => {
  beforeEach(resetStore);

  test('deleting the selected object sets selectedObjectId to null', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        (objWithoutId) => {
          resetStore();

          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(objWithoutId);

          // Select the object
          useDiagramStore.getState().selectObject(id);
          expect(useDiagramStore.getState().selectedObjectId).toBe(id);

          // Delete the selected object
          useDiagramStore.getState().removeCanvasObject(id);

          // Selection should be cleared
          expect(useDiagramStore.getState().selectedObjectId).toBeNull();
        },
      ),
      { numRuns: 100 },
    );
  });

  test('deleting a non-selected object does NOT clear the selection', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        canvasObjectWithoutIdArbitrary(),
        (selectedObjWithoutId, otherObjWithoutId) => {
          resetStore();

          const store = useDiagramStore.getState();
          const selectedId = store.addCanvasObject(selectedObjWithoutId);
          const otherId = useDiagramStore.getState().addCanvasObject(otherObjWithoutId);

          // Select the first object
          useDiagramStore.getState().selectObject(selectedId);
          expect(useDiagramStore.getState().selectedObjectId).toBe(selectedId);

          // Delete the OTHER (non-selected) object
          useDiagramStore.getState().removeCanvasObject(otherId);

          // Selection should still point to the first object
          expect(useDiagramStore.getState().selectedObjectId).toBe(selectedId);
          // The selected object should still exist
          expect(useDiagramStore.getState().canvasObjects.has(selectedId)).toBe(true);
          // The deleted object should be gone
          expect(useDiagramStore.getState().canvasObjects.has(otherId)).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });
});
