import fc from 'fast-check';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary } from '../arbitraries';

function resetStore() {
  useDiagramStore.setState({
    canvasObjects: new Map(),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    clipboard: [],
    connectors: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

/**
 * Simulates the right-click selection logic from Canvas.tsx handleContextMenu:
 *   if (!store.selectedObjectIds.has(objectId)) { store.selectObject(objectId); }
 */
function simulateRightClickSelection(objectId: string) {
  const store = useDiagramStore.getState();
  if (!store.selectedObjectIds.has(objectId)) {
    store.selectObject(objectId);
  }
}

// Feature: canvas-context-menu, Property 1: Right-click selection invariant
// **Validates: Requirements 1.3, 1.4**
describe('Property 1: Right-click selection invariant', () => {
  beforeEach(resetStore);

  it('right-clicking an unselected object makes it the sole selection (or group members if grouped)', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 2, maxLength: 5 }),
        (objects) => {
          resetStore();

          // Add objects to the store
          const ids: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            ids.push(id);
          }

          // Pick a target object index and build a selection that does NOT include it
          const targetIdx = 0;
          const targetId = ids[targetIdx];
          const otherIds = ids.filter((_, i) => i !== targetIdx);

          // Set selection to some subset of other objects (not including target)
          const selectionSubset = otherIds.length > 0 ? new Set(otherIds.slice(0, Math.max(1, Math.floor(otherIds.length / 2)))) : new Set<string>();
          useDiagramStore.setState({ selectedObjectIds: selectionSubset });

          // Verify target is NOT in selection
          expect(useDiagramStore.getState().selectedObjectIds.has(targetId)).toBe(false);

          // Simulate right-click on the unselected target
          simulateRightClickSelection(targetId);

          const state = useDiagramStore.getState();
          const obj = state.canvasObjects.get(targetId)!;

          if (obj.groupId) {
            // If target is in a group, selection should be all group members
            const group = state.objectGroups.get(obj.groupId);
            if (group) {
              expect(state.selectedObjectIds).toEqual(new Set(group.memberIds));
            }
          } else {
            // Target should be the sole selection
            expect(state.selectedObjectIds).toEqual(new Set([targetId]));
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('right-clicking an object already in a multi-selection preserves the entire selection', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 2, maxLength: 5 }),
        fc.integer({ min: 0, max: 4 }),
        (objects, targetIdxRaw) => {
          resetStore();

          // Add objects to the store
          const ids: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            ids.push(id);
          }

          // Pick a valid target index
          const targetIdx = targetIdxRaw % ids.length;
          const targetId = ids[targetIdx];

          // Set selection to ALL objects (multi-selection that includes the target)
          const multiSelection = new Set(ids);
          useDiagramStore.setState({ selectedObjectIds: multiSelection });

          // Snapshot the selection before right-click
          const selectionBefore = new Set(useDiagramStore.getState().selectedObjectIds);

          // Verify target IS in selection
          expect(selectionBefore.has(targetId)).toBe(true);

          // Simulate right-click on the already-selected target
          simulateRightClickSelection(targetId);

          // Selection should be unchanged
          const selectionAfter = useDiagramStore.getState().selectedObjectIds;
          expect(selectionAfter).toEqual(selectionBefore);
        }
      ),
      { numRuns: 100 }
    );
  });
});
