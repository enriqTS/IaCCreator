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

// Feature: canvas-context-menu, Property 10: Lock/unlock round trip
describe('Property 10: Lock/unlock round trip', () => {
  beforeEach(resetStore);

  it('locking then unlocking restores locked to falsy', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        (obj) => {
          resetStore();

          const id = useDiagramStore.getState().addCanvasObject(obj);
          const ids = new Set([id]);

          // Initially unlocked
          expect(useDiagramStore.getState().canvasObjects.get(id)!.locked).toBeFalsy();

          // Lock
          useDiagramStore.getState().toggleLockObjects(ids);
          expect(useDiagramStore.getState().canvasObjects.get(id)!.locked).toBe(true);

          // Unlock
          useDiagramStore.getState().toggleLockObjects(ids);
          expect(useDiagramStore.getState().canvasObjects.get(id)!.locked).toBeFalsy();
        }
      ),
      { numRuns: 100 }
    );
  });
});
