import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import {
  architectureBlockWithoutIdArbitrary,
  geometricObjectWithoutIdArbitrary,
} from './arbitraries';
import { MIN_OBJECT_WIDTH, MIN_OBJECT_HEIGHT } from '@/types/diagram';

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

/**
 * Arbitrary that generates dimension values spanning negative, zero, below-minimum, and above-minimum ranges.
 */
function dimensionArbitrary(): fc.Arbitrary<number> {
  return fc.oneof(
    fc.integer({ min: -1000, max: -1 }),   // negative
    fc.constant(0),                         // zero
    fc.integer({ min: 1, max: 39 }),        // below minimum
    fc.integer({ min: 40, max: 2000 }),     // at or above minimum
  );
}

// Feature: canvas-objects-editor, Property 5: Minimum dimension enforcement
// **Validates: Requirements 4.4, 7.3, 9.6**
describe('Property 5: Minimum dimension enforcement', () => {
  beforeEach(resetStore);

  test('updateCanvasObject clamps dimensions for architecture blocks', () => {
    fc.assert(
      fc.property(
        architectureBlockWithoutIdArbitrary(),
        dimensionArbitrary(),
        dimensionArbitrary(),
        (blockWithoutId, w, h) => {
          resetStore();
          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(blockWithoutId);

          useDiagramStore.getState().updateCanvasObject(id, {
            visualConfig: { width: w, height: h },
          });

          const stored = useDiagramStore.getState().canvasObjects.get(id)!;
          expect(stored.visualConfig.width).toBeGreaterThanOrEqual(MIN_OBJECT_WIDTH);
          expect(stored.visualConfig.height).toBeGreaterThanOrEqual(MIN_OBJECT_HEIGHT);
          expect(stored.visualConfig.width).toBe(Math.max(w, MIN_OBJECT_WIDTH));
          expect(stored.visualConfig.height).toBe(Math.max(h, MIN_OBJECT_HEIGHT));
        },
      ),
      { numRuns: 100 },
    );
  });

  test('updateCanvasObject clamps dimensions for geometric objects', () => {
    fc.assert(
      fc.property(
        geometricObjectWithoutIdArbitrary(),
        dimensionArbitrary(),
        dimensionArbitrary(),
        (geoWithoutId, w, h) => {
          resetStore();
          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(geoWithoutId);

          useDiagramStore.getState().updateCanvasObject(id, {
            visualConfig: { width: w, height: h },
          });

          const stored = useDiagramStore.getState().canvasObjects.get(id)!;
          const vc = stored.visualConfig as { width: number; height: number };
          expect(vc.width).toBeGreaterThanOrEqual(MIN_OBJECT_WIDTH);
          expect(vc.height).toBeGreaterThanOrEqual(MIN_OBJECT_HEIGHT);
          expect(vc.width).toBe(Math.max(w, MIN_OBJECT_WIDTH));
          expect(vc.height).toBe(Math.max(h, MIN_OBJECT_HEIGHT));
        },
      ),
      { numRuns: 100 },
    );
  });

  test('updateVisualConfig clamps dimensions for architecture blocks', () => {
    fc.assert(
      fc.property(
        architectureBlockWithoutIdArbitrary(),
        dimensionArbitrary(),
        dimensionArbitrary(),
        (blockWithoutId, w, h) => {
          resetStore();
          const id = useDiagramStore.getState().addCanvasObject(blockWithoutId);

          useDiagramStore.getState().updateVisualConfig(id, { width: w, height: h });

          const stored = useDiagramStore.getState().canvasObjects.get(id)!;
          expect(stored.visualConfig.width).toBeGreaterThanOrEqual(MIN_OBJECT_WIDTH);
          expect(stored.visualConfig.height).toBeGreaterThanOrEqual(MIN_OBJECT_HEIGHT);
          expect(stored.visualConfig.width).toBe(Math.max(w, MIN_OBJECT_WIDTH));
          expect(stored.visualConfig.height).toBe(Math.max(h, MIN_OBJECT_HEIGHT));
        },
      ),
      { numRuns: 100 },
    );
  });

  test('updateVisualConfig clamps dimensions for geometric objects', () => {
    fc.assert(
      fc.property(
        geometricObjectWithoutIdArbitrary(),
        dimensionArbitrary(),
        dimensionArbitrary(),
        (geoWithoutId, w, h) => {
          resetStore();
          const id = useDiagramStore.getState().addCanvasObject(geoWithoutId);

          useDiagramStore.getState().updateVisualConfig(id, { width: w, height: h });

          const stored = useDiagramStore.getState().canvasObjects.get(id)!;
          const vc = stored.visualConfig as { width: number; height: number };
          expect(vc.width).toBeGreaterThanOrEqual(MIN_OBJECT_WIDTH);
          expect(vc.height).toBeGreaterThanOrEqual(MIN_OBJECT_HEIGHT);
          expect(vc.width).toBe(Math.max(w, MIN_OBJECT_WIDTH));
          expect(vc.height).toBe(Math.max(h, MIN_OBJECT_HEIGHT));
        },
      ),
      { numRuns: 100 },
    );
  });

  test('updateObjectBounds clamps dimensions for architecture blocks', () => {
    fc.assert(
      fc.property(
        architectureBlockWithoutIdArbitrary(),
        dimensionArbitrary(),
        dimensionArbitrary(),
        (blockWithoutId, w, h) => {
          resetStore();
          const id = useDiagramStore.getState().addCanvasObject(blockWithoutId);

          useDiagramStore.getState().updateObjectBounds(id, { width: w, height: h });

          const stored = useDiagramStore.getState().canvasObjects.get(id)!;
          expect(stored.visualConfig.width).toBeGreaterThanOrEqual(MIN_OBJECT_WIDTH);
          expect(stored.visualConfig.height).toBeGreaterThanOrEqual(MIN_OBJECT_HEIGHT);
          expect(stored.visualConfig.width).toBe(Math.max(w, MIN_OBJECT_WIDTH));
          expect(stored.visualConfig.height).toBe(Math.max(h, MIN_OBJECT_HEIGHT));
        },
      ),
      { numRuns: 100 },
    );
  });

  test('updateObjectBounds clamps dimensions for geometric objects', () => {
    fc.assert(
      fc.property(
        geometricObjectWithoutIdArbitrary(),
        dimensionArbitrary(),
        dimensionArbitrary(),
        (geoWithoutId, w, h) => {
          resetStore();
          const id = useDiagramStore.getState().addCanvasObject(geoWithoutId);

          useDiagramStore.getState().updateObjectBounds(id, { width: w, height: h });

          const stored = useDiagramStore.getState().canvasObjects.get(id)!;
          const vc = stored.visualConfig as { width: number; height: number };
          expect(vc.width).toBeGreaterThanOrEqual(MIN_OBJECT_WIDTH);
          expect(vc.height).toBeGreaterThanOrEqual(MIN_OBJECT_HEIGHT);
          expect(vc.width).toBe(Math.max(w, MIN_OBJECT_WIDTH));
          expect(vc.height).toBe(Math.max(h, MIN_OBJECT_HEIGHT));
        },
      ),
      { numRuns: 100 },
    );
  });
});
