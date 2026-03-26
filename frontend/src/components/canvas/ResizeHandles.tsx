'use client';

import { useRef } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasToScreen, screenToCanvas } from '@/utils/viewport';
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
 * Compute the screen-space position for each of the 8 resize handles
 * given the object's center screen position and scaled dimensions.
 */
function getHandleScreenPositions(
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
  const position = object.position;
  const { width, height } = object.visualConfig;
  const screenCenter = canvasToScreen(position, viewport);
  const halfW = (width * viewport.scale) / 2;
  const halfH = (height * viewport.scale) / 2;
  const handlePositions = getHandleScreenPositions(screenCenter.x, screenCenter.y, halfW, halfH);

  const handleMouseDown = (handle: HandlePosition) => (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

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
              left: hp.x - HANDLE_SIZE / 2,
              top: hp.y - HANDLE_SIZE / 2,
              width: HANDLE_SIZE,
              height: HANDLE_SIZE,
              backgroundColor: '#3b82f6',
              border: '1px solid #fff',
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

  const screenStart = canvasToScreen(object.start, viewport);
  const screenEnd = canvasToScreen(object.end, viewport);

  const handleMouseDown = (endpoint: 'start' | 'end') => (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

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

  const CIRCLE_SIZE = 10;

  return (
    <>
      <div
        data-testid="resize-handle-line-start"
        onMouseDown={handleMouseDown('start')}
        style={{
          position: 'absolute',
          left: screenStart.x - CIRCLE_SIZE / 2,
          top: screenStart.y - CIRCLE_SIZE / 2,
          width: CIRCLE_SIZE,
          height: CIRCLE_SIZE,
          borderRadius: '50%',
          backgroundColor: '#3b82f6',
          border: '1px solid #fff',
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
          left: screenEnd.x - CIRCLE_SIZE / 2,
          top: screenEnd.y - CIRCLE_SIZE / 2,
          width: CIRCLE_SIZE,
          height: CIRCLE_SIZE,
          borderRadius: '50%',
          backgroundColor: '#3b82f6',
          border: '1px solid #fff',
          cursor: 'move',
          zIndex: 1000,
          pointerEvents: 'auto',
          boxSizing: 'border-box',
        }}
      />
    </>
  );
}
