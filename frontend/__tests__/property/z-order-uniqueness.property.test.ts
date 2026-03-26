/**
 * Property-based test: Z-index uniqueness invariant
 *
 * **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
 *
 * Property 1: No two objects share the same zIndex after any sequence of z-order operations.
 */
import { describe, it, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary } from '../properties/arbitraries';

/** Collect all zIndex values from the current store state. */
function allZIndices(): number[] {
  return Array.from(useDiagramStore.getState().canvasObjects.values()).map((o) => o.zIndex);
}

/** Assert that all zIndex values are unique. */
function assertUniqueZIndices(): boolean {
  const zValues = allZIndices();
  return new Set(zValues).size === zValues.length;
}

/**
 * Arbitrary that generates a z-order operation name.
 * These map to the store actions: bringToFront, sendToBack, bringForward, sendBackward.
 */
const zOrderOpArbitrary = fc.constantFrom(
  'addCanvasObject' as const,
  'bringToFront' as const,
  'sendToBack' as const,
  'bringForward' as const,
  'sendBackward' as const,
);

type ZOrderOp = 'addCanvasObject' | 'bringToFront' | 'sendToBack' | 'bringForward' | 'sendBackward';

/**
 * Execute a single z-order operation on the store.
 * - addCanvasObject: adds a new random object
 * - bringToFront/sendToBack/bringForward/sendBackward: picks a random existing object
 */
function executeOp(op: ZOrderOp, objectIds: string[], payload?: unknown): void {
  const store = useDiagramStore.getState();

  if (op === 'addCanvasObject') {
    const id = store.addCanvasObject(payload as Parameters<typeof store.addCanvasObject>[0]);
    objectIds.push(id);
    return;
  }

  // For z-order mutations, pick a random existing object
  if (objectIds.length === 0) return;
  const targetId = objectIds[Math.floor(Math.random() * objectIds.length)];

  switch (op) {
    case 'bringToFront':
      store.bringToFront(targetId);
      break;
    case 'sendToBack':
      store.sendToBack(targetId);
      break;
    case 'bringForward':
      store.bringForward(targetId);
      break;
    case 'sendBackward':
      store.sendBackward(targetId);
      break;
  }
}

describe('Z-Order Uniqueness Property', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
    });
  });

  it('Property 1: no two objects share the same zIndex after any sequence of z-order operations', () => {
    /**
     * **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
     *
     * Strategy: Generate a sequence of operations where each operation is either
     * adding a new canvas object or performing a z-order mutation (bringToFront,
     * sendToBack, bringForward, sendBackward) on a randomly chosen existing object.
     * After every operation, verify that all zIndex values remain unique.
     */
    fc.assert(
      fc.property(
        // Generate a sequence of (operation, optional payload) pairs.
        // We start with at least 2 adds to ensure there are objects to reorder,
        // then follow with a random mix of operations.
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 2, maxLength: 6 }).chain((initialPayloads) =>
          fc.array(
            fc.tuple(zOrderOpArbitrary, canvasObjectWithoutIdArbitrary()),
            { minLength: 1, maxLength: 20 },
          ).map((ops) => ({ initialPayloads, ops })),
        ),
        ({ initialPayloads, ops }) => {
          const objectIds: string[] = [];

          // Phase 1: Add initial objects and verify uniqueness after each add
          for (const payload of initialPayloads) {
            executeOp('addCanvasObject', objectIds, payload);
            if (!assertUniqueZIndices()) return false;
          }

          // Phase 2: Execute random sequence of operations
          for (const [op, payload] of ops) {
            executeOp(op, objectIds, payload);
            if (!assertUniqueZIndices()) return false;
          }

          return true;
        },
      ),
      { numRuns: 200 },
    );
  });
});
