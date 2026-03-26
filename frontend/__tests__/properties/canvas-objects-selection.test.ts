import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary } from './arbitraries';

function resetStore() {
  useDiagramStore.setState({
    canvasObjects: new Map(),
    connectors: new Map(),
    elements: new Map(),
    selectedObjectIds: new Set(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

// Feature: canvas-objects-editor, Property 4: Single selection invariant
// **Validates: Requirements 3.4**
describe('Property 4: Single selection invariant', () => {
  beforeEach(resetStore);

  test('after any sequence of selectObject calls, selectedObjectIds contains exactly the last selected value', () => {
    fc.assert(
      fc.property(
        // Generate 1-10 objects to add to the store
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 1, maxLength: 10 }),
        // Generate a sequence of selection actions (indices into added objects, or -1 for null/deselect)
        fc.array(fc.integer({ min: -1, max: 9 }), { minLength: 1, maxLength: 20 }),
        (objects, selectionIndices) => {
          resetStore();

          // Add all objects and collect their IDs
          const ids: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            ids.push(id);
          }

          // Execute each selection action and verify the invariant after each call
          for (const idx of selectionIndices) {
            const selectValue = idx < 0 || idx >= ids.length ? null : ids[idx];
            useDiagramStore.getState().selectObject(selectValue);

            const state = useDiagramStore.getState();

            if (selectValue === null) {
              // selectObject(null) clears the selection
              expect(state.selectedObjectIds.size).toBe(0);
            } else {
              // selectObject(id) sets the selection to exactly {id}
              expect(state.selectedObjectIds.size).toBe(1);
              expect(state.selectedObjectIds.has(selectValue)).toBe(true);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  test('selecting object B after object A results in only B being selected', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        canvasObjectWithoutIdArbitrary(),
        (objA, objB) => {
          resetStore();

          const idA = useDiagramStore.getState().addCanvasObject(objA);
          const idB = useDiagramStore.getState().addCanvasObject(objB);

          // Select A
          useDiagramStore.getState().selectObject(idA);
          expect(useDiagramStore.getState().selectedObjectIds.has(idA)).toBe(true);
          expect(useDiagramStore.getState().selectedObjectIds.size).toBe(1);

          // Select B — A should no longer be selected
          useDiagramStore.getState().selectObject(idB);
          const state = useDiagramStore.getState();

          expect(state.selectedObjectIds.has(idB)).toBe(true);
          expect(state.selectedObjectIds.size).toBe(1);
          expect(state.selectedObjectIds.has(idA)).toBe(false);
        }
      ),
      { numRuns: 100 }
    );
  });
});
