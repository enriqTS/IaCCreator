/**
 * Feature: canvas-context-menu, Property 13: Rename updates object name
 *
 * For any canvas object and any non-empty string, calling
 * updateCanvasObject(id, { name }) should result in the object's name
 * matching the provided string.
 *
 * **Validates: Requirements 7.2**
 */
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary } from '../arbitraries';

function resetStore() {
  useDiagramStore.setState({
    canvasObjects: new Map(),
    selectedObjectIds: new Set(),
    clipboard: [],
    objectGroups: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

describe('Property 13: Rename updates object name', () => {
  beforeEach(resetStore);

  it('should update the object name to the provided non-empty string', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        fc.string({ minLength: 1, maxLength: 50 }),
        (payload, newName) => {
          resetStore();

          const { addCanvasObject, updateCanvasObject, canvasObjects } = useDiagramStore.getState();
          const id = addCanvasObject(payload);

          // Perform rename
          updateCanvasObject(id, { name: newName } as Parameters<typeof updateCanvasObject>[1]);

          const updated = useDiagramStore.getState().canvasObjects.get(id);
          expect(updated).toBeDefined();
          expect(updated!.name).toBe(newName);
        },
      ),
      { numRuns: 100 },
    );
  });
});
