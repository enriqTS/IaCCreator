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

// Feature: canvas-context-menu, Property 6: Duplicate produces offset copies with unique IDs
describe('Property 6: Duplicate produces offset copies with unique IDs', () => {
  beforeEach(resetStore);

  it('each duplicate has a unique ID, position offset by (20,20), and matching properties', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 1, maxLength: 5 }),
        (objects) => {
          resetStore();

          // Add objects and collect their IDs
          const originalIds: string[] = [];
          for (const obj of objects) {
            const id = useDiagramStore.getState().addCanvasObject(obj);
            originalIds.push(id);
          }

          // Select all objects
          useDiagramStore.setState({ selectedObjectIds: new Set(originalIds) });

          // Snapshot originals before duplication
          const originals = new Map<string, ReturnType<typeof useDiagramStore.getState>['canvasObjects'] extends Map<string, infer V> ? V : never>();
          for (const id of originalIds) {
            const obj = useDiagramStore.getState().canvasObjects.get(id)!;
            originals.set(id, { ...obj });
          }

          // Duplicate
          useDiagramStore.getState().duplicateSelectedObjects();

          const state = useDiagramStore.getState();
          const allIds = new Set(state.canvasObjects.keys());

          // Find new IDs (those not in original set)
          const newIds = new Set<string>();
          for (const id of allIds) {
            if (!originals.has(id)) {
              newIds.add(id);
            }
          }

          // Should have created exactly as many duplicates as originals
          expect(newIds.size).toBe(originalIds.length);

          // Each new ID must be unique and not in the original set
          for (const newId of newIds) {
            expect(originals.has(newId)).toBe(false);
          }

          // Verify each duplicate matches an original with offset position
          const duplicates = Array.from(newIds).map((id) => state.canvasObjects.get(id)!);
          const originalsList = originalIds.map((id) => originals.get(id)!);

          for (const dup of duplicates) {
            // Find matching original by objectType and name
            const matchingOriginal = originalsList.find(
              (orig) => orig.objectType === dup.objectType && orig.name === dup.name
            );
            expect(matchingOriginal).toBeDefined();

            if (matchingOriginal) {
              // Verify objectType matches
              expect(dup.objectType).toBe(matchingOriginal.objectType);
              // Verify name matches
              expect(dup.name).toBe(matchingOriginal.name);

              // Verify position offset
              if (dup.objectType === 'line' && matchingOriginal.objectType === 'line') {
                expect(dup.start.x).toBeCloseTo(matchingOriginal.start.x + 20);
                expect(dup.start.y).toBeCloseTo(matchingOriginal.start.y + 20);
                expect(dup.end.x).toBeCloseTo(matchingOriginal.end.x + 20);
                expect(dup.end.y).toBeCloseTo(matchingOriginal.end.y + 20);
              } else if (dup.objectType !== 'line' && matchingOriginal.objectType !== 'line') {
                expect(dup.position.x).toBeCloseTo(matchingOriginal.position.x + 20);
                expect(dup.position.y).toBeCloseTo(matchingOriginal.position.y + 20);
              }

              // Verify visualConfig matches
              expect(dup.visualConfig).toEqual(matchingOriginal.visualConfig);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
