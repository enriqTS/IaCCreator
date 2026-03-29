/**
 * Property-based test: Segment drag undo round-trip
 *
 * Feature: line-segment-manipulation, Property 7: Segment drag undo round-trip
 *
 * **Validates: Requirements 3.7**
 *
 * For any line with custom waypoints resulting from a segment drag, calling undo
 * shall restore the line's waypoints to their state before the drag operation began.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import type { LineObject, Point } from '@/types/diagram';

/** Arbitrary for a canvas Point with reasonable coordinates. */
const pointArb: fc.Arbitrary<Point> = fc.record({
  x: fc.integer({ min: -2000, max: 2000 }),
  y: fc.integer({ min: -2000, max: 2000 }),
});

/** Arbitrary for a non-empty waypoints array (1–6 waypoints). */
const waypointsArb: fc.Arbitrary<Point[]> = fc.array(pointArb, { minLength: 1, maxLength: 6 });

function resetStore() {
  useDiagramStore.setState({
    elements: new Map(),
    connectors: new Map(),
    canvasObjects: new Map(),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

/**
 * Helper: create a line in the store with no initial waypoints.
 * Returns the line ID.
 */
function createLine(): string {
  const store = useDiagramStore.getState();
  return store.addCanvasObject({
    objectType: 'line',
    name: 'test-line',
    start: { x: 0, y: 0 },
    end: { x: 300, y: 200 },
    sourceAnchor: null,
    targetAnchor: null,
    visualConfig: {
      color: '#ffffff',
      borderWidth: 2,
      strokeStyle: 'solid',
      startArrow: false,
      endArrow: false,
      routingMode: 'orthogonal',
    },
  });
}

describe('Feature: line-segment-manipulation, Property 7: Segment drag undo round-trip', () => {
  beforeEach(() => {
    resetStore();
  });

  it('undo after updateLineWaypoints restores waypoints to null (initial state)', () => {
    /**
     * **Validates: Requirements 3.7**
     *
     * Strategy: Create a line (waypoints initially null/undefined).
     * Call updateLineWaypoints with random waypoints (simulating a segment drag commit).
     * Then call undo. Verify the line's waypoints are restored to their pre-drag state (null/undefined).
     */
    fc.assert(
      fc.property(waypointsArb, (waypoints) => {
        resetStore();
        const lineId = createLine();

        // Verify initial state: no waypoints
        const lineBefore = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
        const initialWaypoints = lineBefore.waypoints ?? null;
        expect(initialWaypoints).toBeNull();

        // Simulate segment drag commit: updateLineWaypoints pushes history then sets waypoints
        useDiagramStore.getState().updateLineWaypoints(lineId, waypoints);

        // Verify waypoints were set
        const lineAfterDrag = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
        expect(lineAfterDrag.waypoints).toEqual(waypoints);

        // Undo
        useDiagramStore.getState().undo();

        // Verify waypoints are restored to initial state
        const lineAfterUndo = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
        const restoredWaypoints = lineAfterUndo.waypoints ?? null;
        expect(restoredWaypoints).toBeNull();
      }),
      { numRuns: 100 },
    );
  });

  it('undo after a second updateLineWaypoints restores the first set of waypoints', () => {
    /**
     * **Validates: Requirements 3.7**
     *
     * Strategy: Create a line, set waypoints once (first drag), then set different
     * waypoints (second drag). Undo should restore the first set of waypoints.
     */
    fc.assert(
      fc.property(waypointsArb, waypointsArb, (firstWaypoints, secondWaypoints) => {
        resetStore();
        const lineId = createLine();

        // First drag: set initial waypoints
        useDiagramStore.getState().updateLineWaypoints(lineId, firstWaypoints);

        const lineAfterFirst = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
        expect(lineAfterFirst.waypoints).toEqual(firstWaypoints);

        // Second drag: set different waypoints
        useDiagramStore.getState().updateLineWaypoints(lineId, secondWaypoints);

        const lineAfterSecond = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
        expect(lineAfterSecond.waypoints).toEqual(secondWaypoints);

        // Undo the second drag
        useDiagramStore.getState().undo();

        // Should restore to the first set of waypoints
        const lineAfterUndo = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
        expect(lineAfterUndo.waypoints).toEqual(firstWaypoints);
      }),
      { numRuns: 100 },
    );
  });
});
