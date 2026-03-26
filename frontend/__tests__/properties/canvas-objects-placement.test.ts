import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import {
  architectureBlockWithoutIdArbitrary,
  lineObjectWithoutIdArbitrary,
  geometricObjectWithoutIdArbitrary,
  canvasObjectWithoutIdArbitrary,
  pointArbitrary,
} from './arbitraries';

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

// Feature: canvas-objects-editor, Property 2: Object placement stores correct position
// **Validates: Requirements 2.1, 2.2, 2.3**
describe('Property 2: Object placement stores correct position', () => {
  beforeEach(resetStore);

  test('architecture block placement stores the provided position', () => {
    fc.assert(
      fc.property(
        architectureBlockWithoutIdArbitrary(),
        pointArbitrary(),
        (blockWithoutId, position) => {
          resetStore();

          const objToAdd = { ...blockWithoutId, position };
          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(objToAdd);

          const state = useDiagramStore.getState();
          const stored = state.canvasObjects.get(id);

          expect(stored).toBeDefined();
          expect(stored!.objectType).toBe('architecture-block');
          if (stored!.objectType === 'architecture-block') {
            expect(stored!.position.x).toBe(position.x);
            expect(stored!.position.y).toBe(position.y);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  test('line object placement stores the provided start and end points', () => {
    fc.assert(
      fc.property(
        lineObjectWithoutIdArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        (lineWithoutId, start, end) => {
          resetStore();

          const objToAdd = { ...lineWithoutId, start, end };
          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(objToAdd);

          const state = useDiagramStore.getState();
          const stored = state.canvasObjects.get(id);

          expect(stored).toBeDefined();
          expect(stored!.objectType).toBe('line');
          if (stored!.objectType === 'line') {
            expect(stored!.start.x).toBe(start.x);
            expect(stored!.start.y).toBe(start.y);
            expect(stored!.end.x).toBe(end.x);
            expect(stored!.end.y).toBe(end.y);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  test('geometric object placement stores the provided position', () => {
    fc.assert(
      fc.property(
        geometricObjectWithoutIdArbitrary(),
        pointArbitrary(),
        (geoWithoutId, position) => {
          resetStore();

          const objToAdd = { ...geoWithoutId, position };
          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(objToAdd);

          const state = useDiagramStore.getState();
          const stored = state.canvasObjects.get(id);

          expect(stored).toBeDefined();
          expect(stored!.objectType).toBe('geometric');
          if (stored!.objectType === 'geometric') {
            expect(stored!.position.x).toBe(position.x);
            expect(stored!.position.y).toBe(position.y);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  test('any canvas object type stores its correct position or start/end', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        (objWithoutId, point1, point2) => {
          resetStore();

          let objToAdd;
          if (objWithoutId.objectType === 'architecture-block') {
            objToAdd = { ...objWithoutId, position: point1 };
          } else if (objWithoutId.objectType === 'line') {
            objToAdd = { ...objWithoutId, start: point1, end: point2 };
          } else {
            objToAdd = { ...objWithoutId, position: point1 };
          }

          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(objToAdd);

          const state = useDiagramStore.getState();
          const stored = state.canvasObjects.get(id);

          expect(stored).toBeDefined();

          if (stored!.objectType === 'architecture-block') {
            expect(stored!.position.x).toBe(point1.x);
            expect(stored!.position.y).toBe(point1.y);
          } else if (stored!.objectType === 'line') {
            expect(stored!.start.x).toBe(point1.x);
            expect(stored!.start.y).toBe(point1.y);
            expect(stored!.end.x).toBe(point2.x);
            expect(stored!.end.y).toBe(point2.y);
          } else if (stored!.objectType === 'geometric') {
            expect(stored!.position.x).toBe(point1.x);
            expect(stored!.position.y).toBe(point1.y);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
