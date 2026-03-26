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

// Feature: canvas-objects-editor, Property 1: Object creation assigns unique ID and correct category
// **Validates: Requirements 1.1, 1.2**
describe('Property 1: Object creation assigns unique ID and correct category', () => {
  beforeEach(resetStore);

  test('addCanvasObject produces an object with a valid UUID and the correct objectType', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        (objWithoutId) => {
          resetStore();

          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(objWithoutId);

          const state = useDiagramStore.getState();
          const stored = state.canvasObjects.get(id);

          // Object exists in the store
          expect(stored).toBeDefined();

          // ID is a non-empty string (UUID)
          expect(typeof id).toBe('string');
          expect(id.length).toBeGreaterThan(0);

          // objectType matches the requested category
          expect(stored!.objectType).toBe(objWithoutId.objectType);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('IDs are unique across multiple additions of random object types', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 2, maxLength: 20 }),
        (objects) => {
          resetStore();

          const ids: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            ids.push(id);
          }

          // All IDs are unique
          const uniqueIds = new Set(ids);
          expect(uniqueIds.size).toBe(ids.length);

          // Each stored object has the correct objectType
          const state = useDiagramStore.getState();
          for (let i = 0; i < ids.length; i++) {
            const stored = state.canvasObjects.get(ids[i]);
            expect(stored).toBeDefined();
            expect(stored!.objectType).toBe(objects[i].objectType);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
