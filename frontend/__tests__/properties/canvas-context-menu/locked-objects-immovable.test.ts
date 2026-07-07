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

// Feature: canvas-context-menu, Property 11: Locked objects cannot be moved
describe('Property 11: Locked objects cannot be moved', () => {
  beforeEach(resetStore);

  it('locked object position unchanged while unlocked object moves', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        canvasObjectWithoutIdArbitrary(),
        fc.double({ min: -500, max: 500, noNaN: true, noDefaultInfinity: true }),
        fc.double({ min: -500, max: 500, noNaN: true, noDefaultInfinity: true }),
        (obj1, obj2, dx, dy) => {
          resetStore();

          const lockedId = useDiagramStore.getState().addCanvasObject(obj1);
          const unlockedId = useDiagramStore.getState().addCanvasObject(obj2);

          // Lock the first object
          useDiagramStore.getState().toggleLockObjects(new Set([lockedId]));

          // Snapshot positions before move
          const lockedBefore = { ...useDiagramStore.getState().canvasObjects.get(lockedId)! };
          const unlockedBefore = { ...useDiagramStore.getState().canvasObjects.get(unlockedId)! };

          // Select both and move
          useDiagramStore.setState({
            selectedObjectIds: new Set([lockedId, unlockedId]),
          });
          useDiagramStore.getState().moveSelectedObjects(dx, dy);

          const lockedAfter = useDiagramStore.getState().canvasObjects.get(lockedId)!;
          const unlockedAfter = useDiagramStore.getState().canvasObjects.get(unlockedId)!;

          // Locked object: position unchanged
          if (lockedBefore.objectType === 'line' && lockedAfter.objectType === 'line') {
            expect(lockedAfter.start.x).toBe(lockedBefore.start.x);
            expect(lockedAfter.start.y).toBe(lockedBefore.start.y);
            expect(lockedAfter.end.x).toBe(lockedBefore.end.x);
            expect(lockedAfter.end.y).toBe(lockedBefore.end.y);
          } else if (lockedBefore.objectType !== 'line' && lockedAfter.objectType !== 'line') {
            expect(lockedAfter.position.x).toBe(lockedBefore.position.x);
            expect(lockedAfter.position.y).toBe(lockedBefore.position.y);
          }

          // Unlocked object: position moved by (dx, dy)
          if (unlockedBefore.objectType === 'line' && unlockedAfter.objectType === 'line') {
            expect(unlockedAfter.start.x).toBeCloseTo(unlockedBefore.start.x + dx);
            expect(unlockedAfter.start.y).toBeCloseTo(unlockedBefore.start.y + dy);
            expect(unlockedAfter.end.x).toBeCloseTo(unlockedBefore.end.x + dx);
            expect(unlockedAfter.end.y).toBeCloseTo(unlockedBefore.end.y + dy);
          } else if (unlockedBefore.objectType !== 'line' && unlockedAfter.objectType !== 'line') {
            expect(unlockedAfter.position.x).toBeCloseTo(unlockedBefore.position.x + dx);
            expect(unlockedAfter.position.y).toBeCloseTo(unlockedBefore.position.y + dy);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
