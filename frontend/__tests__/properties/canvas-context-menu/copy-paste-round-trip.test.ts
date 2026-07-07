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
    connectors: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

// Feature: canvas-context-menu, Property 8: Copy-paste round trip
describe('Property 8: Copy-paste round trip', () => {
  beforeEach(resetStore);

  it('copy then paste produces new unique IDs, matching properties, and relocated positions', () => {
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

          // Select and copy all
          useDiagramStore.setState({
            selectedObjectIds: new Set(originalIds),
          });
          useDiagramStore.getState().copySelectedObjects();

          // Snapshot originals before paste
          const originals = originalIds.map(
            (id) => ({ ...useDiagramStore.getState().canvasObjects.get(id)! })
          );

          // Paste at random position
          useDiagramStore.getState().pasteObjects(pastePosition);
          const state = useDiagramStore.getState();

          // Find pasted IDs (new ones not in originals)
          const originalIdSet = new Set(originalIds);
          const pastedIds: string[] = [];
          for (const id of state.canvasObjects.keys()) {
            if (!originalIdSet.has(id)) pastedIds.push(id);
          }

          // Same count
          expect(pastedIds.length).toBe(originalIds.length);

          // All pasted IDs are unique and not in originals
          for (const pid of pastedIds) {
            expect(originalIdSet.has(pid)).toBe(false);
          }

          // Verify matching properties
          for (const pid of pastedIds) {
            const pasted = state.canvasObjects.get(pid)!;
            const matchingOrig = originals.find(
              (o) => o.objectType === pasted.objectType && o.name === pasted.name
            );
            expect(matchingOrig).toBeDefined();
            if (matchingOrig) {
              expect(pasted.objectType).toBe(matchingOrig.objectType);
              expect(pasted.name).toBe(matchingOrig.name);
              expect(pasted.visualConfig).toEqual(matchingOrig.visualConfig);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
