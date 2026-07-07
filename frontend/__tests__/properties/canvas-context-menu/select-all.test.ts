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

// Feature: canvas-context-menu, Property 16: Select all selects every object
describe('Property 16: Select all selects every object', () => {
  beforeEach(resetStore);

  it('selectAllObjects sets selectedObjectIds to all canvasObjects keys', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 1, maxLength: 10 }),
        (objects) => {
          resetStore();

          const ids: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            ids.push(id);
          }

          // Call selectAll
          useDiagramStore.getState().selectAllObjects();

          const state = useDiagramStore.getState();
          const allKeys = new Set(state.canvasObjects.keys());

          // selectedObjectIds should equal all canvasObjects keys
          expect(state.selectedObjectIds.size).toBe(allKeys.size);
          for (const key of allKeys) {
            expect(state.selectedObjectIds.has(key)).toBe(true);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
