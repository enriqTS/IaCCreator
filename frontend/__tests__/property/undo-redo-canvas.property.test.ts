/**
 * Bug Condition Exploration Test: Canvas Object Undo/Redo Not Tracked
 *
 * **Validates: Requirements 1.1, 1.2, 1.6**
 *
 * Property 1: Bug Condition — For any canvas object mutation from the set
 * {removeCanvasObject, updateVisualConfig, groupSelectedObjects, ungroupObjects},
 * performing the mutation then calling undo() should restore canvasObjects and
 * objectGroups to their pre-mutation state.
 *
 * EXPECTED: These tests FAIL on unfixed code, confirming the bug exists.
 * canvasObjects and objectGroups are not included in HistoryEntry, and the
 * discrete canvas mutators never call pushHistory().
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import {
  architectureBlockWithoutIdArbitrary,
  canvasObjectWithoutIdArbitrary,
} from '../properties/arbitraries';

/** Helper: deep-compare two Maps by converting to sorted JSON */
function mapsEqual<K, V>(a: Map<K, V>, b: Map<K, V>): boolean {
  if (a.size !== b.size) return false;
  for (const [key, val] of a) {
    const other = b.get(key);
    if (other === undefined) return false;
    if (JSON.stringify(val) !== JSON.stringify(other)) return false;
  }
  return true;
}

/** Helper: snapshot canvasObjects and objectGroups as deep clones */
function snapshotCanvasState() {
  const { canvasObjects, objectGroups } = useDiagramStore.getState();
  const clonedObjects = new Map<string, unknown>();
  for (const [k, v] of canvasObjects) {
    clonedObjects.set(k, JSON.parse(JSON.stringify(v)));
  }
  const clonedGroups = new Map<string, unknown>();
  for (const [k, v] of objectGroups) {
    clonedGroups.set(k, JSON.parse(JSON.stringify(v)));
  }
  return { canvasObjects: clonedObjects, objectGroups: clonedGroups };
}

function resetStore() {
  useDiagramStore.setState({
    elements: new Map(),
    connectors: new Map(),
    canvasObjects: new Map(),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

describe('Bug Condition Exploration: Canvas Object Undo/Redo Not Tracked', () => {
  beforeEach(() => {
    resetStore();
  });

  /**
   * Test 1: removeCanvasObject → undo → canvasObjects should contain the object again
   *
   * **Validates: Requirements 1.1, 1.6**
   *
   * Bug Condition: removeCanvasObject never calls pushHistory() and
   * HistoryEntry lacks canvasObjects, so undo cannot restore the deleted object.
   */
  it('Test 1: undo after removeCanvasObject should restore the deleted object', () => {
    const store = useDiagramStore.getState();

    const id = store.addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'block-1',
      position: { x: 100, y: 200 },
      config: {},
      visualConfig: { width: 80, height: 80 },
    });

    // Capture state before mutation
    const before = snapshotCanvasState();
    expect(before.canvasObjects.size).toBe(1);

    // Perform mutation
    useDiagramStore.getState().removeCanvasObject(id);
    expect(useDiagramStore.getState().canvasObjects.size).toBe(0);

    // Undo — should restore the object
    useDiagramStore.getState().undo();

    const after = useDiagramStore.getState();
    expect(after.canvasObjects.size).toBe(1);
    expect(after.canvasObjects.has(id)).toBe(true);
  });

  /**
   * Test 2: updateVisualConfig → undo → visualConfig should be restored to original
   *
   * **Validates: Requirements 1.1, 1.6**
   *
   * Bug Condition: updateVisualConfig never calls pushHistory(), so undo
   * cannot restore the previous visual config.
   */
  it('Test 2: undo after updateVisualConfig should restore original visual config', () => {
    const store = useDiagramStore.getState();

    const id = store.addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'block-1',
      position: { x: 0, y: 0 },
      config: {},
      visualConfig: { width: 80, height: 80 },
    });

    // Capture state before mutation
    const objBefore = useDiagramStore.getState().canvasObjects.get(id)!;
    const originalWidth = (objBefore as any).visualConfig.width;
    expect(originalWidth).toBe(80);

    // Perform mutation — change width to 200
    useDiagramStore.getState().updateVisualConfig(id, { width: 200 });
    const objAfterMutation = useDiagramStore.getState().canvasObjects.get(id)!;
    expect((objAfterMutation as any).visualConfig.width).toBe(200);

    // Undo — should restore original width
    useDiagramStore.getState().undo();

    const objAfterUndo = useDiagramStore.getState().canvasObjects.get(id)!;
    expect(objAfterUndo).toBeDefined();
    expect((objAfterUndo as any).visualConfig.width).toBe(80);
  });

  /**
   * Test 3: groupSelectedObjects → undo → objectGroups should be empty and objects ungrouped
   *
   * **Validates: Requirements 1.1, 1.6**
   *
   * Bug Condition: groupSelectedObjects never calls pushHistory() and
   * HistoryEntry lacks objectGroups, so undo cannot dissolve the group.
   */
  it('Test 3: undo after groupSelectedObjects should dissolve the group', () => {
    const store = useDiagramStore.getState();

    const id1 = store.addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'block-1',
      position: { x: 0, y: 0 },
      config: {},
      visualConfig: { width: 80, height: 80 },
    });
    const id2 = store.addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 's3',
      name: 'block-2',
      position: { x: 100, y: 0 },
      config: {},
      visualConfig: { width: 80, height: 80 },
    });

    // Select both objects
    useDiagramStore.getState().selectObject(id1);
    useDiagramStore.getState().toggleObjectSelection(id2);

    // Capture state before grouping
    expect(useDiagramStore.getState().objectGroups.size).toBe(0);

    // Group them
    const groupId = useDiagramStore.getState().groupSelectedObjects();
    expect(groupId).not.toBeNull();
    expect(useDiagramStore.getState().objectGroups.size).toBe(1);

    // Undo — should dissolve the group
    useDiagramStore.getState().undo();

    expect(useDiagramStore.getState().objectGroups.size).toBe(0);
    const obj1 = useDiagramStore.getState().canvasObjects.get(id1);
    const obj2 = useDiagramStore.getState().canvasObjects.get(id2);
    expect(obj1?.groupId).toBeUndefined();
    expect(obj2?.groupId).toBeUndefined();
  });

  /**
   * Test 4: removeCanvasObject → undo → redo → object should be removed again
   *
   * **Validates: Requirements 1.2**
   *
   * Bug Condition: redo() does not restore canvasObjects because HistoryEntry
   * lacks canvasObjects field.
   */
  it('Test 4: redo after undo of removeCanvasObject should remove the object again', () => {
    const store = useDiagramStore.getState();

    const id = store.addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'block-1',
      position: { x: 50, y: 50 },
      config: {},
      visualConfig: { width: 80, height: 80 },
    });

    expect(useDiagramStore.getState().canvasObjects.size).toBe(1);

    // Remove the object
    useDiagramStore.getState().removeCanvasObject(id);
    expect(useDiagramStore.getState().canvasObjects.size).toBe(0);

    // Undo — should restore
    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().canvasObjects.size).toBe(1);

    // Redo — should remove again
    useDiagramStore.getState().redo();
    expect(useDiagramStore.getState().canvasObjects.size).toBe(0);
    expect(useDiagramStore.getState().canvasObjects.has(id)).toBe(false);
  });

  /**
   * Property-based test: For a randomly generated canvas object mutation from the set
   * {removeCanvasObject, updateVisualConfig, groupSelectedObjects, ungroupObjects},
   * performing the mutation then calling undo() should restore canvasObjects and
   * objectGroups to their pre-mutation state.
   *
   * **Validates: Requirements 1.1, 1.2, 1.6**
   */
  it('Property: undo after any discrete canvas mutation restores canvasObjects and objectGroups', () => {
    const mutationType = fc.constantFrom(
      'removeCanvasObject',
      'updateVisualConfig',
      'groupSelectedObjects',
      'ungroupObjects',
    );

    fc.assert(
      fc.property(
        mutationType,
        fc.array(architectureBlockWithoutIdArbitrary(), { minLength: 2, maxLength: 4 }),
        (mutation, initialObjects) => {
          resetStore();
          const store = useDiagramStore.getState();

          // Add initial objects
          const ids: string[] = [];
          for (const obj of initialObjects) {
            const id = store.addCanvasObject(obj);
            ids.push(id);
          }

          // Set up preconditions depending on mutation type
          let canApply = true;

          if (mutation === 'groupSelectedObjects') {
            // Select at least 2 objects for grouping
            useDiagramStore.getState().selectObject(ids[0]);
            useDiagramStore.getState().toggleObjectSelection(ids[1]);
          } else if (mutation === 'ungroupObjects') {
            // First create a group, then we'll ungroup it
            useDiagramStore.getState().selectObject(ids[0]);
            useDiagramStore.getState().toggleObjectSelection(ids[1]);
            const gid = useDiagramStore.getState().groupSelectedObjects();
            if (!gid) canApply = false;
          }

          if (!canApply) return true; // Skip if precondition not met

          // Snapshot state BEFORE the mutation
          const before = snapshotCanvasState();

          // Apply the mutation
          switch (mutation) {
            case 'removeCanvasObject':
              useDiagramStore.getState().removeCanvasObject(ids[0]);
              break;
            case 'updateVisualConfig':
              useDiagramStore.getState().updateVisualConfig(ids[0], { width: 200 });
              break;
            case 'groupSelectedObjects':
              useDiagramStore.getState().groupSelectedObjects();
              break;
            case 'ungroupObjects': {
              const groups = Array.from(useDiagramStore.getState().objectGroups.keys());
              if (groups.length > 0) {
                useDiagramStore.getState().ungroupObjects(groups[0]);
              }
              break;
            }
          }

          // Undo
          useDiagramStore.getState().undo();

          // Assert canvasObjects and objectGroups are restored
          const after = snapshotCanvasState();
          return (
            mapsEqual(before.canvasObjects, after.canvasObjects) &&
            mapsEqual(before.objectGroups, after.objectGroups)
          );
        },
      ),
      { numRuns: 100 },
    );
  });
});
