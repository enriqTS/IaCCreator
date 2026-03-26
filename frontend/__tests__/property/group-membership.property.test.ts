/**
 * Property-based test: Group membership invariant
 *
 * **Validates: Requirements 8.1, 8.7, 8.9**
 *
 * Property 3: Every groupId on a CanvasObject references a valid ObjectGroup,
 * and every ObjectGroup has ≥ 2 members.
 */
import { describe, it, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary } from '../properties/arbitraries';

/**
 * Assert the group membership invariants:
 * 1. Every groupId on a CanvasObject references a valid ObjectGroup in objectGroups
 * 2. Every ObjectGroup has at least 2 members (memberIds.length >= 2)
 */
function assertGroupMembershipInvariant(): boolean {
  const { canvasObjects, objectGroups } = useDiagramStore.getState();

  // Invariant 1: Every groupId on a CanvasObject references a valid ObjectGroup
  for (const obj of canvasObjects.values()) {
    if (obj.groupId !== undefined) {
      if (!objectGroups.has(obj.groupId)) return false;
    }
  }

  // Invariant 2: Every ObjectGroup has at least 2 members
  for (const group of objectGroups.values()) {
    if (group.memberIds.length < 2) return false;
  }

  return true;
}

/**
 * Operation types that affect grouping and/or canvas objects.
 */
type GroupOp =
  | 'addCanvasObject'
  | 'removeCanvasObject'
  | 'groupSelectedObjects'
  | 'ungroupObjects'
  | 'selectObject'
  | 'toggleObjectSelection';

const groupOpArbitrary: fc.Arbitrary<GroupOp> = fc.constantFrom(
  'addCanvasObject',
  'removeCanvasObject',
  'groupSelectedObjects',
  'ungroupObjects',
  'selectObject',
  'toggleObjectSelection',
);

/**
 * Execute a single group-related operation on the store.
 * Tracks objectIds for operations that need an existing object reference.
 */
function executeOp(
  op: GroupOp,
  objectIds: string[],
  payload: unknown,
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
    case 'groupSelectedObjects': {
      store.groupSelectedObjects();
      break;
    }
    case 'ungroupObjects': {
      const groups = Array.from(store.objectGroups.keys());
      if (groups.length === 0) return;
      const groupId = groups[Math.floor(Math.random() * groups.length)];
      store.ungroupObjects(groupId);
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
  }
}

describe('Group Membership Invariant Property', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
    });
  });

  it('Property 3: every groupId on a CanvasObject references a valid ObjectGroup, and every ObjectGroup has >= 2 members', () => {
    /**
     * **Validates: Requirements 8.1, 8.7, 8.9**
     *
     * Strategy: Generate a sequence of operations that add/remove objects,
     * manipulate selection, and create/dissolve groups. After every operation,
     * verify that:
     *   a. Every groupId on a CanvasObject references a valid ObjectGroup in objectGroups
     *   b. Every ObjectGroup has at least 2 members (memberIds.length >= 2)
     */
    fc.assert(
      fc.property(
        // Seed with at least 2 initial objects so grouping is possible, then run random ops
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 2, maxLength: 6 }).chain((initialPayloads) =>
          fc.array(
            fc.tuple(groupOpArbitrary, canvasObjectWithoutIdArbitrary()),
            { minLength: 1, maxLength: 30 },
          ).map((ops) => ({ initialPayloads, ops })),
        ),
        ({ initialPayloads, ops }) => {
          const objectIds: string[] = [];

          // Phase 1: Add initial objects and verify invariant after each add
          for (const payload of initialPayloads) {
            executeOp('addCanvasObject', objectIds, payload);
            if (!assertGroupMembershipInvariant()) return false;
          }

          // Phase 2: Execute random sequence of operations
          for (const [op, payload] of ops) {
            executeOp(op, objectIds, payload);
            if (!assertGroupMembershipInvariant()) return false;
          }

          return true;
        },
      ),
      { numRuns: 200 },
    );
  });
});
