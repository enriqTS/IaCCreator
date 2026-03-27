'use client';

import { useRef } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { screenToCanvas } from '@/utils/viewport';
import type { CanvasObject, Point } from '@/types/diagram';

const HANDLE_SIZE = 8;

type HandlePosition = 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w';

const CURSOR_MAP: Record<HandlePosition, string> = {
  nw: 'nw-resize',
  n: 'n-resize',
  ne: 'ne-resize',
  e: 'e-resize',
  se: 'se-resize',
  s: 's-resize',
  sw: 'sw-resize',
  w: 'w-resize',
};

const HANDLE_POSITIONS: HandlePosition[] = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];

interface ResizeHandlesProps {
  object: CanvasObject;
}

/**
 * Compute the canvas-space position for each of the 8 resize handles
 * given the object's center canvas position and half-dimensions.
 *
 * Since ResizeHandles is rendered inside the viewport transform container,
 * all positions are in canvas coordinates directly.
 */
function getHandleCanvasPositions(
  centerX: number,
  centerY: number,
  halfW: number,
  halfH: number,
): Record<HandlePosition, Point> {
  return {
    nw: { x: centerX - halfW, y: centerY - halfH },
    n:  { x: centerX,         y: centerY - halfH },
    ne: { x: centerX + halfW, y: centerY - halfH },
    e:  { x: centerX + halfW, y: centerY },
    se: { x: centerX + halfW, y: centerY + halfH },
    s:  { x: centerX,         y: centerY + halfH },
    sw: { x: centerX - halfW, y: centerY + halfH },
    w:  { x: centerX - halfW, y: centerY },
  };
}

export default function ResizeHandles({ object }: ResizeHandlesProps) {
  const viewport = useDiagramStore((s) => s.viewport);
  const updateObjectBounds = useDiagramStore((s) => s.updateObjectBounds);
  const updateLineEndpoint = useDiagramStore((s) => s.updateLineEndpoint);
  const updateCanvasObject = useDiagramStore((s) => s.updateCanvasObject);

  const draggingRef = useRef<{
    handle: HandlePosition | 'line-start' | 'line-end';
    startMouse: Point;
    origPosition: Point;
    origWidth: number;
    origHeight: number;
    origStart?: Point;
    origEnd?: Point;
  } | null>(null);

  // --- Line endpoint handles ---
  if (object.objectType === 'line') {
    return (
      <LineEndpointHandles
        object={object}
        viewport={viewport}
        updateLineEndpoint={updateLineEndpoint}
      />
    );
  }

  // --- Block / Geometric: 8 resize handles ---
  // Positions are in canvas coordinates (parent transform container handles viewport)
  const position = object.position;
  const { width, height } = object.visualConfig;
  const halfW = width / 2;
  const halfH = height / 2;
  const handlePositions = getHandleCanvasPositions(position.x, position.y, halfW, halfH);

  // Inverse scale so handles remain a constant screen-pixel size
  const inverseScale = 1 / viewport.scale;
  const handleSizeCanvas = HANDLE_SIZE * inverseScale;

  const handleMouseDown = (handle: HandlePosition) => (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    useDiagramStore.getState().beginDragGesture();

    draggingRef.current = {
      handle,
      startMouse: { x: e.clientX, y: e.clientY },
      origPosition: { ...position },
      origWidth: width,
      origHeight: height,
    };

    const onMouseMove = (ev: MouseEvent) => {
      if (!draggingRef.current) return;
      const { handle: h, startMouse, origPosition: origPos, origWidth: ow, origHeight: oh } = draggingRef.current;

      const dx = (ev.clientX - startMouse.x) / viewport.scale;
      const dy = (ev.clientY - startMouse.y) / viewport.scale;

      let newWidth = ow;
      let newHeight = oh;
      let newX = origPos.x;
      let newY = origPos.y;

      // Horizontal resizing
      if (h === 'nw' || h === 'w' || h === 'sw') {
        newWidth = ow - dx;
        newX = origPos.x + dx / 2;
      } else if (h === 'ne' || h === 'e' || h === 'se') {
        newWidth = ow + dx;
        newX = origPos.x + dx / 2;
      }

      // Vertical resizing
      if (h === 'nw' || h === 'n' || h === 'ne') {
        newHeight = oh - dy;
        newY = origPos.y + dy / 2;
      } else if (h === 'sw' || h === 's' || h === 'se') {
        newHeight = oh + dy;
        newY = origPos.y + dy / 2;
      }

      updateObjectBounds(object.id, { width: newWidth, height: newHeight });
      updateCanvasObject(object.id, { position: { x: newX, y: newY } } as Partial<CanvasObject>);
    };

    const onMouseUp = () => {
      draggingRef.current = null;
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  return (
    <>
      {HANDLE_POSITIONS.map((pos) => {
        const hp = handlePositions[pos];
        return (
          <div
            key={pos}
            data-testid={`resize-handle-${pos}`}
            onMouseDown={handleMouseDown(pos)}
            style={{
              position: 'absolute',
              left: hp.x - handleSizeCanvas / 2,
              top: hp.y - handleSizeCanvas / 2,
              width: handleSizeCanvas,
              height: handleSizeCanvas,
              backgroundColor: '#3b82f6',
              border: `${inverseScale}px solid #fff`,
              cursor: CURSOR_MAP[pos],
              zIndex: 1000,
              pointerEvents: 'auto',
              boxSizing: 'border-box',
            }}
          />
        );
      })}
    </>
  );
}


// --- Line endpoint handles (circular, for start/end) ---

interface LineEndpointHandlesProps {
  object: Extract<CanvasObject, { objectType: 'line' }>;
  viewport: { offsetX: number; offsetY: number; scale: number };
  updateLineEndpoint: (id: string, endpoint: 'start' | 'end', position: Point) => void;
}

function LineEndpointHandles({ object, viewport, updateLineEndpoint }: LineEndpointHandlesProps) {
  const draggingRef = useRef<{
    endpoint: 'start' | 'end';
    origPoint: Point;
  } | null>(null);

  // Use canvas coordinates directly (parent transform container handles viewport)
  const canvasStart = object.start;
  const canvasEnd = object.end;

  // Inverse scale so handles remain a constant screen-pixel size
  const inverseScale = 1 / viewport.scale;
  const CIRCLE_SIZE_CANVAS = 10 * inverseScale;

  const handleMouseDown = (endpoint: 'start' | 'end') => (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    useDiagramStore.getState().beginDragGesture();

    const origPoint = endpoint === 'start' ? { ...object.start } : { ...object.end };
    draggingRef.current = { endpoint, origPoint };

    const onMouseMove = (ev: MouseEvent) => {
      const canvasPos = screenToCanvas({ x: ev.clientX, y: ev.clientY }, viewport);
      updateLineEndpoint(object.id, endpoint, canvasPos);
    };

    const onMouseUp = () => {
      draggingRef.current = null;
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  return (
    <>
      <div
        data-testid="resize-handle-line-start"
        onMouseDown={handleMouseDown('start')}
        style={{
          position: 'absolute',
          left: canvasStart.x - CIRCLE_SIZE_CANVAS / 2,
          top: canvasStart.y - CIRCLE_SIZE_CANVAS / 2,
          width: CIRCLE_SIZE_CANVAS,
          height: CIRCLE_SIZE_CANVAS,
          borderRadius: '50%',
          backgroundColor: '#3b82f6',
          border: `${inverseScale}px solid #fff`,
          cursor: 'move',
          zIndex: 1000,
          pointerEvents: 'auto',
          boxSizing: 'border-box',
        }}
      />
      <div
        data-testid="resize-handle-line-end"
        onMouseDown={handleMouseDown('end')}
        style={{
          position: 'absolute',
          left: canvasEnd.x - CIRCLE_SIZE_CANVAS / 2,
          top: canvasEnd.y - CIRCLE_SIZE_CANVAS / 2,
          width: CIRCLE_SIZE_CANVAS,
          height: CIRCLE_SIZE_CANVAS,
          borderRadius: '50%',
          backgroundColor: '#3b82f6',
          border: `${inverseScale}px solid #fff`,
          cursor: 'move',
          zIndex: 1000,
          pointerEvents: 'auto',
          boxSizing: 'border-box',
        }}
      />
    </>
  );
}
