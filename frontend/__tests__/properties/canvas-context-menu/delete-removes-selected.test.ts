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
    elements: new Map(),
    connectors: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

// Feature: canvas-context-menu, Property 5: Delete removes all selected objects
describe('Property 5: Delete removes all selected objects', () => {
  beforeEach(resetStore);

  it('deleting all selected objects removes them and decreases count', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 2, maxLength: 8 }),
        fc.integer({ min: 1, max: 7 }),
        (objects, selectCount) => {
          resetStore();

          const ids: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            ids.push(id);
          }

          // Select a subset
          const numToSelect = Math.min(selectCount, ids.length);
          const selectedIds = ids.slice(0, numToSelect);
          useDiagramStore.setState({ selectedObjectIds: new Set(selectedIds) });

          const countBefore = useDiagramStore.getState().canvasObjects.size;

          // Delete all selected
          for (const id of selectedIds) {
            useDiagramStore.getState().removeCanvasObject(id);
          }

          const state = useDiagramStore.getState();

          // None of the deleted IDs should exist
          for (const id of selectedIds) {
            expect(state.canvasObjects.has(id)).toBe(false);
          }

          // Count should have decreased by the number deleted
          expect(state.canvasObjects.size).toBe(countBefore - numToSelect);
        }
      ),
      { numRuns: 100 }
    );
  });
});
