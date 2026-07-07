import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import { getAnchorPoints, findSnapAnchorWithPosition, SNAP_THRESHOLD } from '@/utils/anchor';
import { computeOrthogonalWaypoints, MIN_OFFSET } from '@/utils/routing';
import { DEFAULT_LINE_VISUAL } from '@/types/diagram';
import type { DiagramState } from '@/types/serialization';
import type { LineObject, Rect } from '@/types/diagram';

/**
 * Unit tests for fixed connection routing: backward compatibility, anchor computation,
 * snap threshold, orthogonal routing edge cases.
 *
 * Requirements: 1.1, 1.3, 1.5, 2.3, 5.1
 */

/** Helper to reset the store to a clean state */
function resetStore() {
  useDiagramStore.setState({
    connectors: new Map(),
    canvasObjects: new Map(),
    objectGroups: new Map(),
    selectedObjectIds: new Set(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

/** Minimal valid DiagramState for testing */
function minimalDiagramState(overrides: Partial<DiagramState> = {}): DiagramState {
  return {
    version: 3,
    projectName: 'test',
    environments: [],
    elements: [],
    connectors: [],
    viewport: { offsetX: 0, offsetY: 0, scale: 1 },
    canvasObjects: [],
    ...overrides,
  };
}

describe('Backward compatibility: loading diagrams without anchorPosition', () => {
  beforeEach(resetStore);

  it('source defaults to "right" and target defaults to "left" when anchorPosition fields are missing', () => {
    const state = minimalDiagramState({
      canvasObjects: [
        {
          id: 'line-1',
          objectType: 'line',
          name: 'Test Line',
          startX: 100,
          startY: 200,
          endX: 300,
          endY: 200,
          sourceAnchorObjectId: 'obj-a',
          targetAnchorObjectId: 'obj-b',
          // No sourceAnchorPosition or targetAnchorPosition
          visualConfig: {
            color: '#ffffff',
            borderWidth: 2,
            strokeStyle: 'solid',
            startArrow: false,
            endArrow: false,
          },
        },
      ],
    });

    useDiagramStore.getState().loadDiagramState(state);

    const line = useDiagramStore.getState().canvasObjects.get('line-1') as LineObject;
    expect(line).toBeDefined();
    expect(line.sourceAnchor).toEqual({ objectId: 'obj-a', anchorPosition: 'right' });
    expect(line.targetAnchor).toEqual({ objectId: 'obj-b', anchorPosition: 'left' });
  });

  it('preserves explicit anchorPosition values when present', () => {
    const state = minimalDiagramState({
      canvasObjects: [
        {
          id: 'line-2',
          objectType: 'line',
          name: 'Test Line 2',
          startX: 100,
          startY: 100,
          endX: 100,
          endY: 300,
          sourceAnchorObjectId: 'obj-a',
          targetAnchorObjectId: 'obj-b',
          sourceAnchorPosition: 'bottom',
          targetAnchorPosition: 'top',
          visualConfig: {
            color: '#ffffff',
            borderWidth: 2,
            strokeStyle: 'solid',
            startArrow: false,
            endArrow: false,
          },
        },
      ],
    });

    useDiagramStore.getState().loadDiagramState(state);

    const line = useDiagramStore.getState().canvasObjects.get('line-2') as LineObject;
    expect(line.sourceAnchor).toEqual({ objectId: 'obj-a', anchorPosition: 'bottom' });
    expect(line.targetAnchor).toEqual({ objectId: 'obj-b', anchorPosition: 'top' });
  });
});

describe('Backward compatibility: loading diagrams without routingMode', () => {
  beforeEach(resetStore);

  it('defaults routingMode to "orthogonal" when missing from visualConfig', () => {
    const state = minimalDiagramState({
      canvasObjects: [
        {
          id: 'line-3',
          objectType: 'line',
          name: 'Old Line',
          startX: 0,
          startY: 0,
          endX: 100,
          endY: 100,
          visualConfig: {
            color: '#ffffff',
            borderWidth: 2,
            strokeStyle: 'solid',
            startArrow: false,
            endArrow: false,
            // No routingMode
          },
        },
      ],
    });

    useDiagramStore.getState().loadDiagramState(state);

    const line = useDiagramStore.getState().canvasObjects.get('line-3') as LineObject;
    expect(line.visualConfig.routingMode).toBe('orthogonal');
  });
});

describe('Default globalRoutingMode on fresh store', () => {
  it('is "orthogonal" by default', () => {
    // Fresh store state
    expect(useDiagramStore.getState().globalRoutingMode).toBe('orthogonal');
  });

  it('defaults to "orthogonal" when loading a diagram without globalRoutingMode', () => {
    resetStore();
    const state = minimalDiagramState();
    // No globalRoutingMode field
    useDiagramStore.getState().loadDiagramState(state);
    expect(useDiagramStore.getState().globalRoutingMode).toBe('orthogonal');
  });
});

describe('Anchor coordinate computation for 4 positions on a known rect', () => {
  const rect: Rect = { x: 100, y: 200, width: 80, height: 60 };

  it('top anchor is at center-x, top-y', () => {
    const anchors = getAnchorPoints(rect);
    expect(anchors.top).toEqual({ x: 140, y: 200 });
  });

  it('right anchor is at right-x, center-y', () => {
    const anchors = getAnchorPoints(rect);
    expect(anchors.right).toEqual({ x: 180, y: 230 });
  });

  it('bottom anchor is at center-x, bottom-y', () => {
    const anchors = getAnchorPoints(rect);
    expect(anchors.bottom).toEqual({ x: 140, y: 260 });
  });

  it('left anchor is at left-x, center-y', () => {
    const anchors = getAnchorPoints(rect);
    expect(anchors.left).toEqual({ x: 100, y: 230 });
  });
});

describe('findSnapAnchorWithPosition returns null outside threshold', () => {
  const rect: Rect = { x: 100, y: 100, width: 100, height: 100 };

  it('returns null when point is far from all anchors', () => {
    // Anchors are at: top(150,100), right(200,150), bottom(150,200), left(100,150)
    // Point far away from all of them
    const result = findSnapAnchorWithPosition({ x: 500, y: 500 }, rect);
    expect(result).toBeNull();
  });

  it('returns null when point is just outside the default threshold', () => {
    // Top anchor is at (150, 100). Place point just beyond SNAP_THRESHOLD
    const justOutside = { x: 150, y: 100 - SNAP_THRESHOLD - 1 };
    const result = findSnapAnchorWithPosition(justOutside, rect);
    expect(result).toBeNull();
  });

  it('returns anchor when point is within threshold', () => {
    // Top anchor is at (150, 100). Place point just inside threshold
    const justInside = { x: 150, y: 100 - SNAP_THRESHOLD + 1 };
    const result = findSnapAnchorWithPosition(justInside, rect);
    expect(result).not.toBeNull();
    expect(result!.position).toBe('top');
  });
});

describe('Orthogonal routing Case 1: facing, aligned → zero waypoints', () => {
  it('source right → target left at same Y', () => {
    const start = { x: 100, y: 200 };
    const end = { x: 300, y: 200 };
    const waypoints = computeOrthogonalWaypoints(start, 'right', end, 'left');
    expect(waypoints).toEqual([]);
  });

  it('source bottom → target top at same X', () => {
    const start = { x: 200, y: 100 };
    const end = { x: 200, y: 300 };
    const waypoints = computeOrthogonalWaypoints(start, 'bottom', end, 'top');
    expect(waypoints).toEqual([]);
  });
});

describe('Orthogonal routing Case 4: same-side → U-shape waypoints', () => {
  it('source right → target right produces 2 waypoints forming a U-shape', () => {
    const start = { x: 100, y: 100 };
    const end = { x: 200, y: 300 };
    const waypoints = computeOrthogonalWaypoints(start, 'right', end, 'right');

    expect(waypoints).toHaveLength(2);

    // Both waypoints share the same X (the outer edge of the U)
    const outX = Math.max(start.x + MIN_OFFSET, end.x + MIN_OFFSET);
    expect(waypoints[0]).toEqual({ x: outX, y: start.y });
    expect(waypoints[1]).toEqual({ x: outX, y: end.y });

    // Full path is orthogonal
    const path = [start, ...waypoints, end];
    for (let i = 0; i < path.length - 1; i++) {
      const a = path[i];
      const b = path[i + 1];
      expect(a.x === b.x || a.y === b.y).toBe(true);
    }
  });

  it('source top → target top produces 2 waypoints forming a U-shape', () => {
    const start = { x: 100, y: 200 };
    const end = { x: 300, y: 150 };
    const waypoints = computeOrthogonalWaypoints(start, 'top', end, 'top');

    expect(waypoints).toHaveLength(2);

    const outY = Math.min(start.y - MIN_OFFSET, end.y - MIN_OFFSET);
    expect(waypoints[0]).toEqual({ x: start.x, y: outY });
    expect(waypoints[1]).toEqual({ x: end.x, y: outY });
  });
});

describe('Degenerate case: start === end → empty waypoints', () => {
  it('returns empty array when start and end are identical', () => {
    const point = { x: 150, y: 250 };
    const waypoints = computeOrthogonalWaypoints(point, 'right', point, 'left');
    expect(waypoints).toEqual([]);
  });

  it('returns empty array for any anchor position combination when start === end', () => {
    const point = { x: 0, y: 0 };
    const positions = ['top', 'right', 'bottom', 'left'] as const;
    for (const sp of positions) {
      for (const ep of positions) {
        const waypoints = computeOrthogonalWaypoints(point, sp, point, ep);
        expect(waypoints).toEqual([]);
      }
    }
  });
});
