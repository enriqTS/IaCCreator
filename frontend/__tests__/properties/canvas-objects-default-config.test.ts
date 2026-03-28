import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import {
  DEFAULT_BLOCK_VISUAL,
  DEFAULT_LINE_VISUAL,
  DEFAULT_GEO_VISUAL,
  DEFAULT_TEXT_VISUAL,
  DEFAULT_UML_VISUAL,
} from '@/types/diagram';
import {
  architectureBlockWithoutIdArbitrary,
  lineObjectWithoutIdArbitrary,
  geometricObjectWithoutIdArbitrary,
  canvasObjectWithoutIdArbitrary,
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

// Feature: canvas-objects-editor, Property 3: New objects receive default visual config
// **Validates: Requirements 2.4**
describe('Property 3: New objects receive default visual config', () => {
  beforeEach(resetStore);

  test('architecture block created with default visual config stores DEFAULT_BLOCK_VISUAL', () => {
    fc.assert(
      fc.property(
        architectureBlockWithoutIdArbitrary(),
        (blockWithoutId) => {
          resetStore();

          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(blockWithoutId);

          const state = useDiagramStore.getState();
          const stored = state.canvasObjects.get(id);

          expect(stored).toBeDefined();
          expect(stored!.objectType).toBe('architecture-block');
          if (stored!.objectType === 'architecture-block') {
            expect(stored!.visualConfig).toEqual(DEFAULT_BLOCK_VISUAL);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  test('line object created with default visual config stores DEFAULT_LINE_VISUAL', () => {
    fc.assert(
      fc.property(
        lineObjectWithoutIdArbitrary(),
        (lineWithoutId) => {
          resetStore();

          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(lineWithoutId);

          const state = useDiagramStore.getState();
          const stored = state.canvasObjects.get(id);

          expect(stored).toBeDefined();
          expect(stored!.objectType).toBe('line');
          if (stored!.objectType === 'line') {
            expect(stored!.visualConfig).toEqual(DEFAULT_LINE_VISUAL);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  test('geometric object created with default visual config stores DEFAULT_GEO_VISUAL', () => {
    fc.assert(
      fc.property(
        geometricObjectWithoutIdArbitrary(),
        (geoWithoutId) => {
          resetStore();

          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(geoWithoutId);

          const state = useDiagramStore.getState();
          const stored = state.canvasObjects.get(id);

          expect(stored).toBeDefined();
          expect(stored!.objectType).toBe('geometric');
          if (stored!.objectType === 'geometric') {
            // The shape may vary based on the arbitrary, so compare with the payload's shape
            expect(stored!.visualConfig).toEqual({ ...DEFAULT_GEO_VISUAL, shape: geoWithoutId.visualConfig.shape });
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  test('any canvas object type receives the correct default visual config for its category', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        (objWithoutId) => {
          resetStore();

          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(objWithoutId);

          const state = useDiagramStore.getState();
          const stored = state.canvasObjects.get(id);

          expect(stored).toBeDefined();

          if (stored!.objectType === 'architecture-block') {
            expect(stored!.visualConfig).toEqual(DEFAULT_BLOCK_VISUAL);
          } else if (stored!.objectType === 'line') {
            expect(stored!.visualConfig).toEqual(DEFAULT_LINE_VISUAL);
          } else if (stored!.objectType === 'geometric') {
            // Shape may vary based on the arbitrary
            expect(stored!.visualConfig).toEqual({ ...DEFAULT_GEO_VISUAL, shape: (objWithoutId as { visualConfig: { shape: string } }).visualConfig.shape });
          } else if (stored!.objectType === 'text') {
            expect(stored!.visualConfig).toEqual(DEFAULT_TEXT_VISUAL);
          } else if (stored!.objectType === 'uml') {
            expect(stored!.visualConfig).toEqual(DEFAULT_UML_VISUAL);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
