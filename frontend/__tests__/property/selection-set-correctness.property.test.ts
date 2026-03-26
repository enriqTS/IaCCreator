/**
 * Property-based test: Selection set correctness invariant
 *
 * **Validates: Requirements 7.3, 7.7, 7.8**
 *
 * Property 2: Selection set is always a valid subset of canvasObjects keys
 * (every selected ID exists in canvasObjects).
 */
import { describe, it, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary } from '../properties/arbitraries';
import type { Rect } from '@/types/diagram';

/** Assert that selectedObjectIds is a valid subset of canvasObjects keys. */
function assertSelectionSubset(): boolean {
  const { selectedObjectIds, canvasObjects } = useDiagramStore.getState();
  for (const id of selectedObjectIds) {
    if (!canvasObjects.has(id)) return false;
  }
  return true;
}

/**
 * Operation types that affect selection and/or canvas objects.
 */
type SelectionOp =
  | 'addCanvasObject'
  | 'removeCanvasObject'
  | 'selectObject'
  | 'toggleObjectSelection'
  | 'selectObjectsByRect'
  | 'clearSelection';

const selectionOpArbitrary: fc.Arbitrary<SelectionOp> = fc.constantFrom(
  'addCanvasObject',
  'removeCanvasObject',
  'selectObject',
  'toggleObjectSelection',
  'selectObjectsByRect',
  'clearSelection',
);

/**
 * Arbitrary for a Rect used in marquee selection.
 */
const rectArbitrary: fc.Arbitrary<Rect> = fc.record({
  x: fc.double({ min: -10000, max: 10000, noNaN: true, noDefaultInfinity: true }),
  y: fc.double({ min: -10000, max: 10000, noNaN: true, noDefaultInfinity: true }),
  width: fc.double({ min: 0, max: 5000, noNaN: true, noDefaultInfinity: true }),
  height: fc.double({ min: 0, max: 5000, noNaN: true, noDefaultInfinity: true }),
});

/**
 * Execute a single selection-related operation on the store.
 * Tracks objectIds for operations that need an existing object reference.
 */
function executeOp(
  op: SelectionOp,
  objectIds: string[],
  payload: unknown,
  rect: Rect,
): void {
  const store = useDiagramStore.getState();

  switch (op) {
    case 'addCanvasObject': {
      const id = store.addCanvasObject(payload as Parameters<typeof store.addCanvasObject>[0]);
      objectIds.push(id);
      break;
    }
    case 'removeCanvasObject': {
      if (objectIds.length === 0) return;
      const idx = Math.floor(Math.random() * objectIds.length);
      const targetId = objectIds[idx];
      store.removeCanvasObject(targetId);
      objectIds.splice(idx, 1);
      break;
    }
    case 'selectObject': {
      if (objectIds.length === 0) {
        store.selectObject(null);
      } else {
        const targetId = objectIds[Math.floor(Math.random() * objectIds.length)];
        store.selectObject(targetId);
      }
      break;
    }
    case 'toggleObjectSelection': {
      if (objectIds.length === 0) return;
      const targetId = objectIds[Math.floor(Math.random() * objectIds.length)];
      store.toggleObjectSelection(targetId);
      break;
    }
    case 'selectObjectsByRect': {
      store.selectObjectsByRect(rect);
      break;
    }
    case 'clearSelection': {
      store.clearSelection();
      break;
    }
  }
}

describe('Selection Set Correctness Property', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
    });
  });

  it('Property 2: selectedObjectIds is always a valid subset of canvasObjects keys after any sequence of operations', () => {
    /**
     * **Validates: Requirements 7.3, 7.7, 7.8**
     *
     * Strategy: Generate a sequence of operations that add/remove objects and
     * manipulate the selection set. After every operation, verify that every ID
     * in selectedObjectIds exists as a key in canvasObjects.
     */
    fc.assert(
      fc.property(
        // Seed with some initial objects, then run a random mix of operations
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 1, maxLength: 5 }).chain((initialPayloads) =>
          fc.array(
            fc.tuple(selectionOpArbitrary, canvasObjectWithoutIdArbitrary(), rectArbitrary),
            { minLength: 1, maxLength: 30 },
          ).map((ops) => ({ initialPayloads, ops })),
        ),
        ({ initialPayloads, ops }) => {
          const objectIds: string[] = [];

          // Phase 1: Add initial objects and verify invariant after each add
          for (const payload of initialPayloads) {
            executeOp('addCanvasObject', objectIds, payload, { x: 0, y: 0, width: 0, height: 0 });
            if (!assertSelectionSubset()) return false;
          }

          // Phase 2: Execute random sequence of operations
          for (const [op, payload, rect] of ops) {
            executeOp(op, objectIds, payload, rect);
            if (!assertSelectionSubset()) return false;
          }

          return true;
        },
      ),
      { numRuns: 200 },
    );
  });
});
