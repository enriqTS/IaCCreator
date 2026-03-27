import fc from 'fast-check';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary, pointArbitrary } from '../arbitraries';

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

// Feature: canvas-context-menu, Property 9: Selection updates to pasted objects
describe('Property 9: Selection updates to pasted objects', () => {
  beforeEach(resetStore);

  it('after paste, selectedObjectIds contains exactly the pasted object IDs', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 1, maxLength: 5 }),
        pointArbitrary(),
        (objects, pastePosition) => {
          resetStore();

          const originalIds: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            originalIds.push(id);
          }

          // Select and copy
          useDiagramStore.setState({ selectedObjectIds: new Set(originalIds) });
          useDiagramStore.getState().copySelectedObjects();

          // Paste
          useDiagramStore.getState().pasteObjects(pastePosition);
          const state = useDiagramStore.getState();

          // Find pasted IDs
          const originalIdSet = new Set(originalIds);
          const pastedIds = new Set<string>();
          for (const id of state.canvasObjects.keys()) {
            if (!originalIdSet.has(id)) pastedIds.add(id);
          }

          // selectedObjectIds should be exactly the pasted IDs
          expect(state.selectedObjectIds.size).toBe(pastedIds.size);
          for (const pid of pastedIds) {
            expect(state.selectedObjectIds.has(pid)).toBe(true);
          }

          // No original IDs in selection
          for (const origId of originalIds) {
            expect(state.selectedObjectIds.has(origId)).toBe(false);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
