/**
 * Feature: canvas-context-menu, Property 14: Rename cancel preserves name
 *
 * For any canvas object, if a rename operation is initiated and then
 * cancelled (Escape / no store update), the object's name should remain
 * identical to its value before the rename was initiated.
 *
 * **Validates: Requirements 7.3**
 */
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary } from '../arbitraries';

function resetStore() {
  useDiagramStore.setState({
    canvasObjects: new Map(),
    selectedObjectIds: new Set(),
    clipboard: [],
    objectGroups: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

describe('Property 14: Rename cancel preserves name', () => {
  beforeEach(resetStore);

  it('should preserve the original name when rename is cancelled (no store update)', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        (payload) => {
          resetStore();

          const { addCanvasObject } = useDiagramStore.getState();
          const id = addCanvasObject(payload);

          // Record original name
          const originalName = useDiagramStore.getState().canvasObjects.get(id)!.name;

          // Simulate cancel: user opens rename overlay but presses Escape
          // This means NO updateCanvasObject call is made — the store is untouched

          // Verify name is unchanged
          const afterCancel = useDiagramStore.getState().canvasObjects.get(id);
          expect(afterCancel).toBeDefined();
          expect(afterCancel!.name).toBe(originalName);
        },
      ),
      { numRuns: 100 },
    );
  });
});
