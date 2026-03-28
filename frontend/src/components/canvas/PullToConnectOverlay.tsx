'use client';

import { useState, useEffect, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { findSnapAnchor } from '@/utils/anchor';
import { getObjectBounds } from '@/types/diagram';
import { DEFAULT_LINE_VISUAL } from '@/types/diagram';
import type { Point } from '@/types/diagram';

export default function PullToConnectOverlay() {
  const pullConnectState = useDiagramStore((s) => s.pullConnectState);
  const setPullConnectState = useDiagramStore((s) => s.setPullConnectState);
  const addCanvasObject = useDiagramStore((s) => s.addCanvasObject);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const viewport = useDiagramStore((s) => s.viewport);

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
      let snappedPoint: Point | null = null;

      for (const [objId, obj] of canvasObjects) {
        // Skip the source object and line objects
        if (objId === pullConnectState.sourceObjectId) continue;
        if (obj.objectType === 'line') continue;

        const bounds = getObjectBounds(obj);
        const snap = findSnapAnchor(dropPoint, bounds);
        if (snap) {
          targetObjectId = objId;
          snappedPoint = snap;
          break;
        }
      }

      if (targetObjectId && snappedPoint) {
        // Create an anchored line
        addCanvasObject({
          objectType: 'line',
          name: 'Line',
          start: pullConnectState.sourceAnchorPoint,
          end: snappedPoint,
          sourceAnchor: { objectId: pullConnectState.sourceObjectId },
          targetAnchor: { objectId: targetObjectId },
          visualConfig: { ...DEFAULT_LINE_VISUAL },
        });
      } else {
        // Create a free-floating line
        addCanvasObject({
          objectType: 'line',
          name: 'Line',
          start: pullConnectState.sourceAnchorPoint,
          end: dropPoint,
          sourceAnchor: { objectId: pullConnectState.sourceObjectId },
          targetAnchor: null,
          visualConfig: { ...DEFAULT_LINE_VISUAL },
        });
      }

      setPullConnectState(null);
      setMousePos(null);
    },
    [pullConnectState, viewport, canvasObjects, addCanvasObject, setPullConnectState],
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
      <line
        data-testid="pull-to-connect-preview-line"
        x1={pullConnectState.sourceAnchorPoint.x}
        y1={pullConnectState.sourceAnchorPoint.y}
        x2={mousePos.x}
        y2={mousePos.y}
        stroke="#3b82f6"
        strokeWidth={2}
        strokeDasharray="6 4"
        opacity={0.8}
      />
    </svg>
  );
}
