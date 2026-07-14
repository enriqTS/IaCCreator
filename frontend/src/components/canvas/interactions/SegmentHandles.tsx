'use client';

import { useRef, useState } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { snapToGrid } from '@/utils/snap';
import { findNearestAnchorPosition } from '@/utils/anchor';
import { getConnectionBounds } from '@/utils/bounds-utils';
import type { LineObject, Point } from '@/types/diagram';

const HANDLE_SIZE = 8;

interface SegmentHandlesProps {
  line: LineObject;
  pathPoints: Point[];
}

export type SegmentOrientation = 'horizontal' | 'vertical';

export interface DraggableSegment {
  index: number; // index of the first point in pathPoints
  orientation: SegmentOrientation;
  midpoint: Point;
  p1: Point;
  p2: Point;
}

/**
 * Identify which segments of the path are draggable.
 * A segment is draggable if:
 * - It is not the first or last segment
 * - It is horizontal (same y) or vertical (same x)
 * Horizontal segments can be dragged vertically, vertical segments horizontally.
 */
export function computeDraggableSegments(pathPoints: Point[]): DraggableSegment[] {
  if (pathPoints.length < 4) return []; // Need at least 4 points for a middle segment

  const segments: DraggableSegment[] = [];
  // Skip first segment (index 0) and last segment (index length-2)
  for (let i = 1; i < pathPoints.length - 2; i++) {
    const p1 = pathPoints[i];
    const p2 = pathPoints[i + 1];

    let orientation: SegmentOrientation | null = null;
    if (p1.y === p2.y) {
      orientation = 'horizontal';
    } else if (p1.x === p2.x) {
      orientation = 'vertical';
    }

    if (orientation) {
      segments.push({
        index: i,
        orientation,
        midpoint: {
          x: (p1.x + p2.x) / 2,
          y: (p1.y + p2.y) / 2,
        },
        p1,
        p2,
      });
    }
  }

  return segments;
}

/**
 * Compute new waypoints after dragging a segment.
 * pathPoints includes start and end, so waypoints are pathPoints[1..n-2].
 * The dragged segment at index `segIndex` has its two points updated.
 * After updating, collapse zero-length segments (consecutive identical points).
 */
export function computeNewWaypoints(
  pathPoints: Point[],
  segIndex: number,
  orientation: SegmentOrientation,
  delta: number,
): Point[] {
  // Clone all path points
  const updated = pathPoints.map((p) => ({ ...p }));

  // Apply the drag delta to the segment's two endpoints
  if (orientation === 'horizontal') {
    // Horizontal segment dragged vertically: change y
    updated[segIndex].y += delta;
    updated[segIndex + 1].y += delta;
  } else {
    // Vertical segment dragged horizontally: change x
    updated[segIndex].x += delta;
    updated[segIndex + 1].x += delta;
  }

  // Extract waypoints (exclude start and end)
  const waypoints = updated.slice(1, updated.length - 1);

  // Collapse zero-length segments: remove consecutive duplicate points
  const collapsed: Point[] = [];
  for (const wp of waypoints) {
    if (collapsed.length === 0) {
      collapsed.push(wp);
    } else {
      const prev = collapsed[collapsed.length - 1];
      if (prev.x !== wp.x || prev.y !== wp.y) {
        collapsed.push(wp);
      }
    }
  }

  return collapsed;
}

/**
 * After committing waypoints, evaluate whether the route now passes closer
 * to a different anchor position on connected objects. If so, update the anchor.
 */
function evaluateAdaptiveAnchors(
  line: LineObject,
  newWaypoints: Point[],
  store: ReturnType<typeof useDiagramStore.getState>,
  canvasObjects: Map<string, import('@/types/diagram').CanvasObject>,
): void {
  const fullPath = [line.start, ...newWaypoints, line.end];
  let anchorChanged = false;

  // Evaluate source anchor — use the second waypoint (first turn) as reference
  // This captures the direction the route goes after leaving the source
  if (line.sourceAnchor) {
    const sourceObj = canvasObjects.get(line.sourceAnchor.objectId);
    if (sourceObj) {
      const sourceBounds = getConnectionBounds(sourceObj);
      // Use the waypoint after the first turn (index 2) if available,
      // otherwise the first waypoint, otherwise the end
      const refIdx = Math.min(2, fullPath.length - 1);
      const refPt = fullPath[refIdx];
      const nearest = findNearestAnchorPosition(refPt, sourceBounds, line.sourceAnchor.anchorPosition);
      if (nearest !== line.sourceAnchor.anchorPosition) {
        store.updateLineAnchorPosition(line.id, 'source', nearest);
        anchorChanged = true;
      }
    }
  }

  // Evaluate target anchor — use the second-to-last turn point as reference
  if (line.targetAnchor) {
    const targetObj = canvasObjects.get(line.targetAnchor.objectId);
    if (targetObj) {
      const targetBounds = getConnectionBounds(targetObj);
      const refIdx = Math.max(0, fullPath.length - 3);
      const refPt = fullPath[refIdx];
      const nearest = findNearestAnchorPosition(refPt, targetBounds, line.targetAnchor.anchorPosition);
      if (nearest !== line.targetAnchor.anchorPosition) {
        store.updateLineAnchorPosition(line.id, 'target', nearest);
        anchorChanged = true;
      }
    }
  }

  // When an anchor switches, the user-modified waypoints are no longer valid
  // for the new anchor configuration — clear them so routing recomputes cleanly.
  if (anchorChanged) {
    store.updateLineWaypoints(line.id, null);
  }
}

export default function SegmentHandles({ line, pathPoints }: SegmentHandlesProps) {
  const viewport = useDiagramStore((s) => s.viewport);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);

  const [dragState, setDragState] = useState<{
    segIndex: number;
    orientation: SegmentOrientation;
    delta: number;
    p1: Point;
    p2: Point;
  } | null>(null);

  const draggingRef = useRef<{
    segIndex: number;
    orientation: SegmentOrientation;
    startMouseCoord: number; // screen coordinate along drag axis
    origCoord: number; // original canvas coordinate of the segment
    p1: Point;
    p2: Point;
  } | null>(null);

  // Don't render for locked lines
  if (line.locked) return null;

  const draggableSegments = computeDraggableSegments(pathPoints);
  if (draggableSegments.length === 0 && !dragState) return null;

  const inverseScale = 1 / viewport.scale;
  const handleSizeCanvas = HANDLE_SIZE * inverseScale;

  const handleMouseDown = (segment: DraggableSegment) => (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    useDiagramStore.getState().beginDragGesture();

    const startMouseCoord = segment.orientation === 'horizontal'
      ? e.clientY
      : e.clientX;

    const origCoord = segment.orientation === 'horizontal'
      ? segment.p1.y
      : segment.p1.x;

    draggingRef.current = {
      segIndex: segment.index,
      orientation: segment.orientation,
      startMouseCoord,
      origCoord,
      p1: { ...segment.p1 },
      p2: { ...segment.p2 },
    };

    const onMouseMove = (ev: MouseEvent) => {
      if (!draggingRef.current) return;
      const { orientation, startMouseCoord: startCoord, origCoord: orig, segIndex, p1, p2 } = draggingRef.current;

      const currentMouseCoord = orientation === 'horizontal' ? ev.clientY : ev.clientX;
      let delta = (currentMouseCoord - startCoord) / viewport.scale;

      // Snap to grid when enabled and Alt not held
      const { snapToGridEnabled, gridCellSize } = useLayoutPreferencesStore.getState();
      if (snapToGridEnabled && !ev.altKey) {
        const snappedCoord = snapToGrid(orig + delta, gridCellSize);
        delta = snappedCoord - orig;
      }

      setDragState({
        segIndex,
        orientation,
        delta,
        p1,
        p2,
      });
    };

    const onMouseUp = (ev: MouseEvent) => {
      if (!draggingRef.current) return;
      const { orientation, startMouseCoord: startCoord, origCoord: orig, segIndex } = draggingRef.current;

      const currentMouseCoord = orientation === 'horizontal' ? ev.clientY : ev.clientX;
      let delta = (currentMouseCoord - startCoord) / viewport.scale;

      // Snap to grid when enabled and Alt not held
      const { snapToGridEnabled, gridCellSize } = useLayoutPreferencesStore.getState();
      if (snapToGridEnabled && !ev.altKey) {
        const snappedCoord = snapToGrid(orig + delta, gridCellSize);
        delta = snappedCoord - orig;
      }

      // Compute new waypoints
      const newWaypoints = computeNewWaypoints(pathPoints, segIndex, orientation, delta);

      // Commit waypoints
      const store = useDiagramStore.getState();
      store.updateLineWaypoints(line.id, newWaypoints.length > 0 ? newWaypoints : null);

      // Adaptive anchor switching
      evaluateAdaptiveAnchors(line, newWaypoints, store, canvasObjects);

      // Clean up
      draggingRef.current = null;
      setDragState(null);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  return (
    <>
      {/* Segment handles */}
      {draggableSegments.map((seg) => {
        const cursor = seg.orientation === 'horizontal' ? 'ns-resize' : 'ew-resize';
        return (
          <div
            key={`seg-handle-${seg.index}`}
            data-testid={`segment-handle-${seg.index}`}
            onMouseDown={handleMouseDown(seg)}
            style={{
              position: 'absolute',
              left: seg.midpoint.x - handleSizeCanvas / 2,
              top: seg.midpoint.y - handleSizeCanvas / 2,
              width: handleSizeCanvas,
              height: handleSizeCanvas,
              backgroundColor: '#3b82f6',
              border: `${inverseScale}px solid #fff`,
              cursor,
              zIndex: 1001,
              pointerEvents: 'auto',
              boxSizing: 'border-box',
            }}
          />
        );
      })}

      {/* Drag preview: dashed line showing new segment position */}
      {dragState && (
        <svg
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            overflow: 'visible',
            zIndex: 1000,
          }}
        >
          {dragState.orientation === 'horizontal' ? (
            <line
              x1={dragState.p1.x}
              y1={dragState.p1.y + dragState.delta}
              x2={dragState.p2.x}
              y2={dragState.p2.y + dragState.delta}
              stroke="#3b82f6"
              strokeWidth={2 * inverseScale}
              strokeDasharray={`${4 * inverseScale} ${3 * inverseScale}`}
            />
          ) : (
            <line
              x1={dragState.p1.x + dragState.delta}
              y1={dragState.p1.y}
              x2={dragState.p2.x + dragState.delta}
              y2={dragState.p2.y}
              stroke="#3b82f6"
              strokeWidth={2 * inverseScale}
              strokeDasharray={`${4 * inverseScale} ${3 * inverseScale}`}
            />
          )}
        </svg>
      )}
    </>
  );
}
