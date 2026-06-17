'use client';

import { useState, useEffect, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { findSnapAnchorWithPosition } from '@/utils/anchor';
import type { AnchorPosition } from '@/utils/anchor';
import { getObjectBounds } from '@/types/diagram';
import { DEFAULT_LINE_VISUAL } from '@/types/diagram';
import type { Point } from '@/types/diagram';
import { computeOrthogonalWaypoints, inferAnchorPosition } from '@/utils/routing';

/** Build an SVG path `d` attribute from an array of points using M and L commands */
export function buildPathD(points: Point[]): string {
  if (points.length === 0) return '';
  const [first, ...rest] = points;
  return `M ${first.x} ${first.y}` + rest.map((p) => ` L ${p.x} ${p.y}`).join('');
}

export default function PullToConnectOverlay() {
  const pullConnectState = useDiagramStore((s) => s.pullConnectState);
  const setPullConnectState = useDiagramStore((s) => s.setPullConnectState);
  const addCanvasObject = useDiagramStore((s) => s.addCanvasObject);
  const addConnector = useDiagramStore((s) => s.addConnector);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const connectors = useDiagramStore((s) => s.connectors);
  const viewport = useDiagramStore((s) => s.viewport);
  const globalRoutingMode = useDiagramStore((s) => s.globalRoutingMode);

  const [mousePos, setMousePos] = useState<Point | null>(null);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!pullConnectState) return;
      // Convert screen coordinates to canvas coordinates
      const canvasX = (e.clientX - viewport.offsetX) / viewport.scale;
      const canvasY = (e.clientY - viewport.offsetY) / viewport.scale;
      setMousePos({ x: canvasX, y: canvasY });
    },
    [pullConnectState, viewport],
  );

  const handleMouseUp = useCallback(
    (e: MouseEvent) => {
      if (!pullConnectState) return;

      const canvasX = (e.clientX - viewport.offsetX) / viewport.scale;
      const canvasY = (e.clientY - viewport.offsetY) / viewport.scale;
      const dropPoint: Point = { x: canvasX, y: canvasY };

      // Try to find a snap target on another object
      let targetObjectId: string | null = null;
      let snapResult: { point: Point; position: AnchorPosition } | null = null;

      for (const [objId, obj] of canvasObjects) {
        // Skip the source object and line objects
        if (objId === pullConnectState.sourceObjectId) continue;
        if (obj.objectType === 'line') continue;

        const bounds = getObjectBounds(obj);
        const snap = findSnapAnchorWithPosition(dropPoint, bounds);
        if (snap) {
          targetObjectId = objId;
          snapResult = snap;
          break;
        }
      }

      const { sourceAnchorPosition } = pullConnectState;

      if (targetObjectId && snapResult) {
        // Create an anchored line
        addCanvasObject({
          objectType: 'line',
          name: 'Line',
          start: pullConnectState.sourceAnchorPoint,
          end: snapResult.point,
          sourceAnchor: { objectId: pullConnectState.sourceObjectId, anchorPosition: sourceAnchorPosition },
          targetAnchor: { objectId: targetObjectId, anchorPosition: snapResult.position },
          visualConfig: { ...DEFAULT_LINE_VISUAL, routingMode: globalRoutingMode },
        });

        // Auto-create a Connector (logical connection) if both source and target are architecture blocks.
        // This is intentional: the Connector tool requires both endpoints to be Architecture_Blocks,
        // unlike Object Picker freeform line/arrow placement which has no such restriction.
        const sourceObj = canvasObjects.get(pullConnectState.sourceObjectId);
        const targetObj = canvasObjects.get(targetObjectId);
        if (
          sourceObj && sourceObj.objectType === 'architecture-block' &&
          targetObj && targetObj.objectType === 'architecture-block'
        ) {
          // Only create if a connector doesn't already exist for this pair
          let connectorExists = false;
          for (const conn of connectors.values()) {
            if (conn.sourceId === pullConnectState.sourceObjectId && conn.targetId === targetObjectId) {
              connectorExists = true;
              break;
            }
          }
          if (!connectorExists) {
            addConnector(pullConnectState.sourceObjectId, targetObjectId, 'triggers');
          }
        }
      } else {
        // Create a free-floating line
        addCanvasObject({
          objectType: 'line',
          name: 'Line',
          start: pullConnectState.sourceAnchorPoint,
          end: dropPoint,
          sourceAnchor: { objectId: pullConnectState.sourceObjectId, anchorPosition: sourceAnchorPosition },
          targetAnchor: null,
          visualConfig: { ...DEFAULT_LINE_VISUAL, routingMode: globalRoutingMode },
        });
      }

      setPullConnectState(null);
      setMousePos(null);
    },
    [pullConnectState, viewport, canvasObjects, addCanvasObject, addConnector, connectors, setPullConnectState, globalRoutingMode],
  );

  useEffect(() => {
    if (!pullConnectState) return;

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [pullConnectState, handleMouseMove, handleMouseUp]);

  if (!pullConnectState || !mousePos) return null;

  const sourcePoint = pullConnectState.sourceAnchorPoint;

  // --- Snap-target detection ---
  // Iterate over all canvas objects excluding the source object and line objects.
  // For each eligible object, check if the cursor is within snap threshold of an anchor.
  // Track the closest snap result (smallest Euclidean distance) across all eligible objects.
  let closestSnap: { point: Point; position: AnchorPosition } | null = null;
  let closestSnapDistSq = Infinity;

  for (const [objId, obj] of canvasObjects) {
    if (objId === pullConnectState.sourceObjectId) continue;
    if (obj.objectType === 'line') continue;

    const bounds = getObjectBounds(obj);
    const snap = findSnapAnchorWithPosition(mousePos, bounds);
    if (snap) {
      const dx = snap.point.x - mousePos.x;
      const dy = snap.point.y - mousePos.y;
      const distSq = dx * dx + dy * dy;
      if (distSq < closestSnapDistSq) {
        closestSnapDistSq = distSq;
        closestSnap = snap;
      }
    }
  }

  // Determine endpoint and end direction based on snap state
  const endpoint: Point = closestSnap ? closestSnap.point : mousePos;
  const endDirection: AnchorPosition = closestSnap
    ? closestSnap.position
    : inferAnchorPosition(mousePos, sourcePoint);

  // Determine the rendering element based on routing mode
  let previewElement: React.ReactNode;

  if (globalRoutingMode === 'orthogonal') {
    const waypoints = computeOrthogonalWaypoints(
      sourcePoint,
      pullConnectState.sourceAnchorPosition,
      endpoint,
      endDirection,
    );
    const pathPoints = [sourcePoint, ...waypoints, endpoint];

    if (pathPoints.length >= 2) {
      previewElement = (
        <path
          data-testid="pull-to-connect-preview-line"
          d={buildPathD(pathPoints)}
          fill="none"
          stroke="#3b82f6"
          strokeWidth={2}
          strokeDasharray="6 4"
          opacity={0.8}
        />
      );
    } else {
      // Fallback to line when fewer than 2 total path points
      previewElement = (
        <line
          data-testid="pull-to-connect-preview-line"
          x1={sourcePoint.x}
          y1={sourcePoint.y}
          x2={endpoint.x}
          y2={endpoint.y}
          stroke="#3b82f6"
          strokeWidth={2}
          strokeDasharray="6 4"
          opacity={0.8}
        />
      );
    }
  } else {
    // Diagonal mode: preserve existing <line> rendering behavior
    previewElement = (
      <line
        data-testid="pull-to-connect-preview-line"
        x1={sourcePoint.x}
        y1={sourcePoint.y}
        x2={endpoint.x}
        y2={endpoint.y}
        stroke="#3b82f6"
        strokeWidth={2}
        strokeDasharray="6 4"
        opacity={0.8}
      />
    );
  }

  return (
    <svg
      data-testid="pull-to-connect-overlay"
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        overflow: 'visible',
      }}
    >
      {previewElement}
    </svg>
  );
}
