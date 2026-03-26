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

// Feature: canvas-objects-editor, Property 4: Single selection invariant
// **Validates: Requirements 3.4**
describe('Property 4: Single selection invariant', () => {
  beforeEach(resetStore);

  test('after any sequence of selectObject calls, selectedObjectId is always the last selected value', () => {
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

            // The selectedObjectId must be exactly the last value passed to selectObject
            expect(state.selectedObjectId).toBe(selectValue);

            // The selectedObjectId is either null or a single string ID — never an array or multiple values
            if (state.selectedObjectId !== null) {
              expect(typeof state.selectedObjectId).toBe('string');
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
          expect(useDiagramStore.getState().selectedObjectId).toBe(idA);

          // Select B — A should no longer be selected
          useDiagramStore.getState().selectObject(idB);
          const state = useDiagramStore.getState();

          expect(state.selectedObjectId).toBe(idB);
          expect(state.selectedObjectId).not.toBe(idA);
        }
      ),
      { numRuns: 100 }
    );
  });
});
