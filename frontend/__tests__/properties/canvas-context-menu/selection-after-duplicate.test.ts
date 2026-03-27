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

// Feature: canvas-context-menu, Property 7: Selection updates to duplicated objects
describe('Property 7: Selection updates to duplicated objects', () => {
  beforeEach(resetStore);

  it('after duplication, selectedObjectIds contains exactly the new duplicate IDs and none of the originals', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 1, maxLength: 5 }),
        (objects) => {
          resetStore();

          const originalIds: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            originalIds.push(id);
          }

          // Select all originals
          useDiagramStore.setState({ selectedObjectIds: new Set(originalIds) });

          // Duplicate
          useDiagramStore.getState().duplicateSelectedObjects();

          const state = useDiagramStore.getState();

          // Selection should not contain any original IDs
          for (const origId of originalIds) {
            expect(state.selectedObjectIds.has(origId)).toBe(false);
          }

          // Selection should contain only new IDs
          for (const selectedId of state.selectedObjectIds) {
            expect(originalIds.includes(selectedId)).toBe(false);
          }

          // Number of selected should equal number of originals
          expect(state.selectedObjectIds.size).toBe(originalIds.length);

          // All selected IDs should exist in canvasObjects
          for (const selectedId of state.selectedObjectIds) {
            expect(state.canvasObjects.has(selectedId)).toBe(true);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
