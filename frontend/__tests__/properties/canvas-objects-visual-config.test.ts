import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import {
  architectureBlockWithoutIdArbitrary,
  lineObjectWithoutIdArbitrary,
  geometricObjectWithoutIdArbitrary,
  strokeStyleArbitrary,
  geometricShapeArbitrary,
} from './arbitraries';
import {
  MIN_OBJECT_WIDTH,
  MIN_OBJECT_HEIGHT,
} from '@/types/diagram';
import type {
  ArchitectureBlockVisualConfig,
  LineVisualConfig,
  GeometricVisualConfig,
} from '@/types/diagram';

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

/** Strip undefined keys so spread doesn't overwrite with undefined. */
function stripUndefined<T extends Record<string, unknown>>(obj: T): Partial<T> {
  const result: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined) result[k] = v;
  }
  return result as Partial<T>;
}

const HEX_CHARS = '0123456789abcdef'.split('');

/** Generates a random hex color string like "#a3f1b2". */
function hexColorArbitrary(): fc.Arbitrary<string> {
  return fc
    .array(fc.constantFrom(...HEX_CHARS), { minLength: 6, maxLength: 6 })
    .map((chars) => `#${chars.join('')}`);
}

/**
 * Generates a random partial ArchitectureBlockVisualConfig update.
 * At least one field is always present (undefined keys are stripped).
 */
function partialBlockVisualArbitrary(): fc.Arbitrary<Partial<ArchitectureBlockVisualConfig>> {
  return fc
    .record({
      width: fc.option(fc.integer({ min: -100, max: 2000 }), { nil: undefined }),
      height: fc.option(fc.integer({ min: -100, max: 2000 }), { nil: undefined }),
    })
    .map(stripUndefined)
    .filter((r) => Object.keys(r).length > 0) as fc.Arbitrary<Partial<ArchitectureBlockVisualConfig>>;
}

/**
 * Generates a random partial LineVisualConfig update.
 * At least one field is always present (undefined keys are stripped).
 */
function partialLineVisualArbitrary(): fc.Arbitrary<Partial<LineVisualConfig>> {
  return fc
    .record({
      color: fc.option(hexColorArbitrary(), { nil: undefined }),
      borderWidth: fc.option(fc.integer({ min: 1, max: 20 }), { nil: undefined }),
      strokeStyle: fc.option(strokeStyleArbitrary(), { nil: undefined }),
      startArrow: fc.option(fc.boolean(), { nil: undefined }),
      endArrow: fc.option(fc.boolean(), { nil: undefined }),
    })
    .map(stripUndefined)
    .filter((r) => Object.keys(r).length > 0) as fc.Arbitrary<Partial<LineVisualConfig>>;
}

/**
 * Generates a random partial GeometricVisualConfig update.
 * At least one field is always present (undefined keys are stripped).
 */
function partialGeoVisualArbitrary(): fc.Arbitrary<Partial<GeometricVisualConfig>> {
  return fc
    .record({
      width: fc.option(fc.integer({ min: -100, max: 2000 }), { nil: undefined }),
      height: fc.option(fc.integer({ min: -100, max: 2000 }), { nil: undefined }),
      fill: fc.option(fc.boolean(), { nil: undefined }),
      fillColor: fc.option(hexColorArbitrary(), { nil: undefined }),
      borderColor: fc.option(hexColorArbitrary(), { nil: undefined }),
      borderWidth: fc.option(fc.integer({ min: 1, max: 20 }), { nil: undefined }),
      shape: fc.option(geometricShapeArbitrary(), { nil: undefined }),
    })
    .map(stripUndefined)
    .filter((r) => Object.keys(r).length > 0) as fc.Arbitrary<Partial<GeometricVisualConfig>>;
}

// Feature: canvas-objects-editor, Property 6: Visual config updates persist in store
// **Validates: Requirements 4.2, 4.3, 4.5, 6.2, 7.2, 8.2, 8.3, 9.5**
describe('Property 6: Visual config updates persist in store', () => {
  beforeEach(resetStore);

  test('updateVisualConfig merges partial updates for architecture blocks, clamping dimensions', () => {
    fc.assert(
      fc.property(
        architectureBlockWithoutIdArbitrary(),
        partialBlockVisualArbitrary(),
        (blockWithoutId, partialUpdate) => {
          resetStore();
          const id = useDiagramStore.getState().addCanvasObject(blockWithoutId);
          const before = { ...useDiagramStore.getState().canvasObjects.get(id)!.visualConfig } as ArchitectureBlockVisualConfig;

          useDiagramStore.getState().updateVisualConfig(id, partialUpdate);

          const after = useDiagramStore.getState().canvasObjects.get(id)!.visualConfig as ArchitectureBlockVisualConfig;

          // Updated fields have the new values (with min dimension clamping)
          if (partialUpdate.width !== undefined) {
            expect(after.width).toBe(Math.max(partialUpdate.width, MIN_OBJECT_WIDTH));
          } else {
            expect(after.width).toBe(before.width);
          }

          if (partialUpdate.height !== undefined) {
            expect(after.height).toBe(Math.max(partialUpdate.height, MIN_OBJECT_HEIGHT));
          } else {
            expect(after.height).toBe(before.height);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  test('updateVisualConfig merges partial updates for line objects, non-updated fields unchanged', () => {
    fc.assert(
      fc.property(
        lineObjectWithoutIdArbitrary(),
        partialLineVisualArbitrary(),
        (lineWithoutId, partialUpdate) => {
          resetStore();
          const id = useDiagramStore.getState().addCanvasObject(lineWithoutId);
          const before = { ...useDiagramStore.getState().canvasObjects.get(id)!.visualConfig } as LineVisualConfig;

          useDiagramStore.getState().updateVisualConfig(id, partialUpdate);

          const after = useDiagramStore.getState().canvasObjects.get(id)!.visualConfig as LineVisualConfig;

          // Updated fields have the new values
          if (partialUpdate.color !== undefined) {
            expect(after.color).toBe(partialUpdate.color);
          } else {
            expect(after.color).toBe(before.color);
          }

          if (partialUpdate.borderWidth !== undefined) {
            expect(after.borderWidth).toBe(partialUpdate.borderWidth);
          } else {
            expect(after.borderWidth).toBe(before.borderWidth);
          }

          if (partialUpdate.strokeStyle !== undefined) {
            expect(after.strokeStyle).toBe(partialUpdate.strokeStyle);
          } else {
            expect(after.strokeStyle).toBe(before.strokeStyle);
          }

          if (partialUpdate.startArrow !== undefined) {
            expect(after.startArrow).toBe(partialUpdate.startArrow);
          } else {
            expect(after.startArrow).toBe(before.startArrow);
          }

          if (partialUpdate.endArrow !== undefined) {
            expect(after.endArrow).toBe(partialUpdate.endArrow);
          } else {
            expect(after.endArrow).toBe(before.endArrow);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  test('updateVisualConfig merges partial updates for geometric objects, clamping dimensions', () => {
    fc.assert(
      fc.property(
        geometricObjectWithoutIdArbitrary(),
        partialGeoVisualArbitrary(),
        (geoWithoutId, partialUpdate) => {
          resetStore();
          const id = useDiagramStore.getState().addCanvasObject(geoWithoutId);
          const before = { ...useDiagramStore.getState().canvasObjects.get(id)!.visualConfig } as GeometricVisualConfig;

          useDiagramStore.getState().updateVisualConfig(id, partialUpdate);

          const after = useDiagramStore.getState().canvasObjects.get(id)!.visualConfig as GeometricVisualConfig;

          // Dimension fields: clamped to minimum
          if (partialUpdate.width !== undefined) {
            expect(after.width).toBe(Math.max(partialUpdate.width, MIN_OBJECT_WIDTH));
          } else {
            expect(after.width).toBe(before.width);
          }

          if (partialUpdate.height !== undefined) {
            expect(after.height).toBe(Math.max(partialUpdate.height, MIN_OBJECT_HEIGHT));
          } else {
            expect(after.height).toBe(before.height);
          }

          // Non-dimension fields: exact match
          if (partialUpdate.fill !== undefined) {
            expect(after.fill).toBe(partialUpdate.fill);
          } else {
            expect(after.fill).toBe(before.fill);
          }

          if (partialUpdate.fillColor !== undefined) {
            expect(after.fillColor).toBe(partialUpdate.fillColor);
          } else {
            expect(after.fillColor).toBe(before.fillColor);
          }

          if (partialUpdate.borderColor !== undefined) {
            expect(after.borderColor).toBe(partialUpdate.borderColor);
          } else {
            expect(after.borderColor).toBe(before.borderColor);
          }

          if (partialUpdate.borderWidth !== undefined) {
            expect(after.borderWidth).toBe(partialUpdate.borderWidth);
          } else {
            expect(after.borderWidth).toBe(before.borderWidth);
          }

          if (partialUpdate.shape !== undefined) {
            expect(after.shape).toBe(partialUpdate.shape);
          } else {
            expect(after.shape).toBe(before.shape);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
