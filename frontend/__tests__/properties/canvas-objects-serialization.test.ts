import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary } from './arbitraries';

function resetStore() {
  useDiagramStore.setState({
    canvasObjects: new Map(),
    connectors: new Map(),
    selectedObjectIds: new Set(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
    projectName: '',
    environments: [],
    viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
  });
}

// Feature: canvas-objects-editor, Property 8: Visual config serialization round trip
// **Validates: Requirements 10.1, 10.2, 10.3**
describe('Property 8: Visual config serialization round trip', () => {
  beforeEach(resetStore);

  test('serializing and deserializing canvas objects produces equivalent objects', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 1, maxLength: 10 }),
        (objectsWithoutId) => {
          resetStore();

          // 1. Add random canvas objects to the store
          const addedIds: string[] = [];
          for (const obj of objectsWithoutId) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            addedIds.push(id);
          }

          // Capture the original objects from the store
          const originalObjects = new Map(useDiagramStore.getState().canvasObjects);

          // 2. Serialize the diagram state
          const serialized = useDiagramStore.getState().serializeDiagramState();

          // 3. Reset the store
          resetStore();

          // Verify store is empty after reset
          expect(useDiagramStore.getState().canvasObjects.size).toBe(0);

          // 4. Load the serialized state
          useDiagramStore.getState().loadDiagramState(serialized);

          // 5. Verify deserialized canvas objects match originals
          const deserialized = useDiagramStore.getState().canvasObjects;

          // Same number of objects
          expect(deserialized.size).toBe(originalObjects.size);

          // Each original object should have an equivalent deserialized counterpart
          for (const [id, original] of originalObjects) {
            const restored = deserialized.get(id);
            expect(restored).toBeDefined();
            expect(restored!.id).toBe(original.id);
            expect(restored!.objectType).toBe(original.objectType);
            expect(restored!.name).toBe(original.name);

            // Check type-specific fields
            if (original.objectType === 'architecture-block' && restored!.objectType === 'architecture-block') {
              expect(restored!.position.x).toBe(original.position.x);
              expect(restored!.position.y).toBe(original.position.y);
              expect(restored!.serviceType).toBe(original.serviceType);
              expect(restored!.config).toEqual(original.config);
              expect(restored!.visualConfig).toEqual(original.visualConfig);
            } else if (original.objectType === 'line' && restored!.objectType === 'line') {
              expect(restored!.start.x).toBe(original.start.x);
              expect(restored!.start.y).toBe(original.start.y);
              expect(restored!.end.x).toBe(original.end.x);
              expect(restored!.end.y).toBe(original.end.y);
              expect(restored!.visualConfig).toEqual(original.visualConfig);
            } else if (original.objectType === 'geometric' && restored!.objectType === 'geometric') {
              expect(restored!.position.x).toBe(original.position.x);
              expect(restored!.position.y).toBe(original.position.y);
              expect(restored!.visualConfig).toEqual(original.visualConfig);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
