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

// Feature: canvas-context-menu, Property 15: Group/ungroup round trip
describe('Property 15: Group/ungroup round trip', () => {
  beforeEach(resetStore);

  it('grouping then ungrouping restores all objects to no groupId and removes the group', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 2, maxLength: 6 }),
        (objects) => {
          resetStore();

          const ids: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            ids.push(id);
          }

          // Select all objects
          useDiagramStore.setState({ selectedObjectIds: new Set(ids) });

          // Group
          const groupId = useDiagramStore.getState().groupSelectedObjects();
          expect(groupId).not.toBeNull();

          // Verify group was created
          expect(useDiagramStore.getState().objectGroups.has(groupId!)).toBe(true);

          // Verify all objects have groupId set
          for (const id of ids) {
            expect(useDiagramStore.getState().canvasObjects.get(id)!.groupId).toBe(groupId);
          }

          // Ungroup
          useDiagramStore.getState().ungroupObjects(groupId!);

          const state = useDiagramStore.getState();

          // Group should be removed
          expect(state.objectGroups.has(groupId!)).toBe(false);

          // All objects should have no groupId
          for (const id of ids) {
            const obj = state.canvasObjects.get(id)!;
            expect(obj.groupId).toBeUndefined();
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
