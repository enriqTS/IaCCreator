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

// Feature: canvas-context-menu, Property 12: Locked objects can be selected
describe('Property 12: Locked objects can be selected', () => {
  beforeEach(resetStore);

  it('a locked object can be selected via selectObject', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        (obj) => {
          resetStore();

          const id = useDiagramStore.getState().addCanvasObject(obj);

          // Lock the object
          useDiagramStore.getState().toggleLockObjects(new Set([id]));
          expect(useDiagramStore.getState().canvasObjects.get(id)!.locked).toBe(true);

          // Select the locked object
          useDiagramStore.getState().selectObject(id);

          // Verify it's in selectedObjectIds
          expect(useDiagramStore.getState().selectedObjectIds.has(id)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });
});
