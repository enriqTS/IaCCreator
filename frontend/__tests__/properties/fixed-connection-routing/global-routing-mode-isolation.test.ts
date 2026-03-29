import fc from 'fast-check';
import { describe, test, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { RoutingMode, LineObject } from '@/types/diagram';
import { DEFAULT_LINE_VISUAL } from '@/types/diagram';

// Feature: fixed-connection-routing
// **Property 7: Global routing mode inheritance and isolation**
// **Validates: Requirements 4.2, 5.2, 5.3**

const ROUTING_MODES: RoutingMode[] = ['orthogonal', 'diagonal'];

function routingModeArbitrary(): fc.Arbitrary<RoutingMode> {
  return fc.constantFrom(...ROUTING_MODES);
}

/**
 * Generates a non-empty array of routing modes representing
 * the routingMode for each pre-existing line.
 */
function existingLineModesArbitrary(): fc.Arbitrary<RoutingMode[]> {
  return fc.array(routingModeArbitrary(), { minLength: 1, maxLength: 10 });
}

/**
 * Helper: create a line via addCanvasObject with a specific routingMode.
 */
function createLine(routingMode: RoutingMode): string {
  return useDiagramStore.getState().addCanvasObject({
    objectType: 'line',
    name: 'Line',
    start: { x: 0, y: 0 },
    end: { x: 100, y: 100 },
    sourceAnchor: null,
    targetAnchor: null,
    visualConfig: { ...DEFAULT_LINE_VISUAL, routingMode },
  });
}

function getLine(id: string): LineObject {
  return useDiagramStore.getState().canvasObjects.get(id) as LineObject;
}

describe('Property 7: Global routing mode inheritance and isolation', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      globalRoutingMode: 'orthogonal',
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  test('a new line created with routingMode from globalRoutingMode inherits that mode, and existing lines remain unchanged', () => {
    fc.assert(
      fc.property(
        routingModeArbitrary(),
        existingLineModesArbitrary(),
        (globalMode, existingModes) => {
          // Reset store for each iteration
          useDiagramStore.setState({
            canvasObjects: new Map(),
            selectedObjectIds: new Set(),
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });

          // Create pre-existing lines with known routing modes
          const existingIds = existingModes.map((mode) => createLine(mode));

          // Set the global routing mode
          useDiagramStore.getState().setGlobalRoutingMode(globalMode);

          // Snapshot existing lines' routing modes before creating the new line
          const snapshotBefore = existingIds.map((id) => ({
            id,
            routingMode: getLine(id).visualConfig.routingMode,
          }));

          // Create a new line using the current globalRoutingMode
          const currentGlobal = useDiagramStore.getState().globalRoutingMode;
          const newLineId = createLine(currentGlobal);

          // The new line's routingMode must match globalRoutingMode
          const newLine = getLine(newLineId);
          expect(newLine.visualConfig.routingMode).toBe(globalMode);

          // All existing lines must retain their original routingMode
          for (const { id, routingMode } of snapshotBefore) {
            const line = getLine(id);
            expect(line.visualConfig.routingMode).toBe(routingMode);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  test('changing globalRoutingMode does not mutate any existing line routingMode', () => {
    fc.assert(
      fc.property(
        routingModeArbitrary(),
        routingModeArbitrary(),
        existingLineModesArbitrary(),
        (initialGlobal, newGlobal, existingModes) => {
          // Reset store
          useDiagramStore.setState({
            canvasObjects: new Map(),
            selectedObjectIds: new Set(),
            globalRoutingMode: initialGlobal,
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });

          // Create existing lines
          const existingIds = existingModes.map((mode) => createLine(mode));

          // Snapshot before changing global mode
          const snapshotBefore = existingIds.map((id) => ({
            id,
            routingMode: getLine(id).visualConfig.routingMode,
          }));

          // Change the global routing mode
          useDiagramStore.getState().setGlobalRoutingMode(newGlobal);

          // Verify no existing line was affected
          for (const { id, routingMode } of snapshotBefore) {
            const line = getLine(id);
            expect(line.visualConfig.routingMode).toBe(routingMode);
          }

          // Verify the global mode actually changed
          expect(useDiagramStore.getState().globalRoutingMode).toBe(newGlobal);
        },
      ),
      { numRuns: 100 },
    );
  });
});
