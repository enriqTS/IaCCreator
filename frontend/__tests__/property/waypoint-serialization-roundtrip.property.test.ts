/**
 * Property-based test: Waypoint serialization round-trip
 *
 * Feature: line-segment-manipulation, Property 8: Waypoint serialization round-trip
 *
 * **Validates: Requirements 3.8**
 *
 * For any LineObject with custom waypoints, serializing the diagram state and then
 * deserializing it should produce a LineObject with identical waypoints (same number
 * of points, same coordinates).
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { pointArbitrary } from '../properties/arbitraries';
import type { Point, LineObject } from '@/types/diagram';
import { DEFAULT_LINE_VISUAL } from '@/types/diagram';

/** Arbitrary for a non-empty array of waypoints (1–10 points). */
const waypointsArbitrary = fc.array(pointArbitrary(), { minLength: 1, maxLength: 10 });

function resetStore() {
  useDiagramStore.setState({
    canvasObjects: new Map(),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    connectors: new Map(),
    viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    projectName: '',
    environments: [],
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

describe('Feature: line-segment-manipulation, Property 8: Waypoint serialization round-trip', () => {
  beforeEach(() => {
    resetStore();
  });

  it('serializing and deserializing preserves waypoints on LineObjects', () => {
    /**
     * **Validates: Requirements 3.8**
     *
     * Strategy:
     * 1. Generate random start/end points and a random array of waypoints
     * 2. Create a line object in the store with those waypoints
     * 3. Serialize the diagram state
     * 4. Reset the store and load the serialized state
     * 5. Verify the deserialized line has identical waypoints (count and coordinates)
     */
    fc.assert(
      fc.property(
        pointArbitrary(),
        pointArbitrary(),
        waypointsArbitrary,
        (start: Point, end: Point, waypoints: Point[]) => {
          resetStore();

          const store = useDiagramStore.getState();

          // Add a line object with waypoints
          const lineId = store.addCanvasObject({
            objectType: 'line',
            name: 'test-line',
            start,
            end,
            sourceAnchor: null,
            targetAnchor: null,
            waypoints,
            visualConfig: { ...DEFAULT_LINE_VISUAL },
          });

          // Verify the line was added with waypoints
          const preLine = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
          expect(preLine).toBeDefined();
          expect(preLine.waypoints).toBeDefined();
          expect(preLine.waypoints!.length).toBe(waypoints.length);

          // Serialize
          const serialized = useDiagramStore.getState().serializeDiagramState();

          // Reset store completely
          resetStore();

          // Load from serialized state
          useDiagramStore.getState().loadDiagramState(serialized);

          // Retrieve the deserialized line
          const postLine = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
          expect(postLine).toBeDefined();
          expect(postLine.objectType).toBe('line');

          // Verify waypoints match: same count
          expect(postLine.waypoints).toBeDefined();
          expect(postLine.waypoints).not.toBeNull();
          expect(postLine.waypoints!.length).toBe(waypoints.length);

          // Verify each waypoint coordinate matches
          for (let i = 0; i < waypoints.length; i++) {
            expect(postLine.waypoints![i].x).toBe(waypoints[i].x);
            expect(postLine.waypoints![i].y).toBe(waypoints[i].y);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
