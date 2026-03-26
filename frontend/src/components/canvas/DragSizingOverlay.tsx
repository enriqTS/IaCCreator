'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { screenToCanvas } from '@/utils/viewport';
import { MIN_OBJECT_WIDTH, MIN_OBJECT_HEIGHT, DEFAULT_GEO_VISUAL } from '@/types/diagram';
import type { Point, GeometricShape } from '@/types/diagram';

/** Minimum drag distance (px) in either axis to count as a drag vs. a click */
const DRAG_THRESHOLD = 5;

interface PlaceObjectPayload {
  canvasPosition: Point;
  width: number;
  height: number;
}

interface DragSizingOverlayProps {
  containerRef: React.RefObject<HTMLDivElement | null>;
  onPlaceObject: (payload: PlaceObjectPayload) => void;
}

export default function DragSizingOverlay({ containerRef, onPlaceObject }: DragSizingOverlayProps) {
  const activeTool = useDiagramStore((s) => s.activeTool);
  const viewport = useDiagramStore((s) => s.viewport);

  const isPlacement =
    (typeof activeTool === 'object' && activeTool.type === 'place-service') ||
    (typeof activeTool === 'object' && activeTool.type === 'place-shape');

  // Drag state stored in refs for performance (avoid re-renders on every mousemove)
  const isDragging = useRef(false);
  const originScreen = useRef<Point | null>(null);

  // We use state for the current mouse position so the rectangle re-renders
  const [dragRect, setDragRect] = useState<{
    originScreen: Point;
    currentScreen: Point;
  } | null>(null);

  const getContainerOffset = useCallback((): Point | null => {
    const container = containerRef.current;
    if (!container) return null;
    const rect = container.getBoundingClientRect();
    return { x: rect.left, y: rect.top };
  }, [containerRef]);

  // --- Mouse handlers ---

  useEffect(() => {
    if (!isPlacement) {
      // Reset state when leaving placement mode
      isDragging.current = false;
      originScreen.current = null;
      setDragRect(null);
      return;
    }

    const container = containerRef.current;
    if (!container) return;

    const handleMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return; // left-click only

      const offset = getContainerOffset();
      if (!offset) return;

      const screenPt: Point = { x: e.clientX - offset.x, y: e.clientY - offset.y };
      isDragging.current = true;
      originScreen.current = screenPt;
      setDragRect({ originScreen: screenPt, currentScreen: screenPt });

      // Prevent default to avoid text selection during drag
      e.preventDefault();
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current || !originScreen.current) return;

      const offset = getContainerOffset();
      if (!offset) return;

      const screenPt: Point = { x: e.clientX - offset.x, y: e.clientY - offset.y };
      setDragRect({ originScreen: originScreen.current, currentScreen: screenPt });
    };

    const handleMouseUp = (e: MouseEvent) => {
      if (e.button !== 0 || !isDragging.current || !originScreen.current) return;

      const offset = getContainerOffset();
      if (!offset) return;

      const endScreen: Point = { x: e.clientX - offset.x, y: e.clientY - offset.y };
      const origin = originScreen.current;

      // Read viewport at commit time from the store
      const currentViewport = useDiagramStore.getState().viewport;

      // Convert both points to canvas coordinates
      const originCanvas = screenToCanvas(origin, currentViewport);
      const endCanvas = screenToCanvas(endScreen, currentViewport);

      const rawWidth = Math.abs(endCanvas.x - originCanvas.x);
      const rawHeight = Math.abs(endCanvas.y - originCanvas.y);

      const isDrag = rawWidth >= DRAG_THRESHOLD || rawHeight >= DRAG_THRESHOLD;

      if (isDrag) {
        // Enforce minimum dimensions
        const width = Math.max(rawWidth, MIN_OBJECT_WIDTH);
        const height = Math.max(rawHeight, MIN_OBJECT_HEIGHT);

        // Position is the center of the dragged rectangle
        const minX = Math.min(originCanvas.x, endCanvas.x);
        const minY = Math.min(originCanvas.y, endCanvas.y);
        const canvasPosition: Point = {
          x: minX + width / 2,
          y: minY + height / 2,
        };

        onPlaceObject({ canvasPosition, width, height });
      } else {
        // Small drag → treat as click, use default dimensions (caller decides defaults)
        onPlaceObject({ canvasPosition: originCanvas, width: 0, height: 0 });
      }

      // Reset
      isDragging.current = false;
      originScreen.current = null;
      setDragRect(null);
    };

    container.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      container.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isPlacement, containerRef, getContainerOffset, onPlaceObject]);

  // --- Render ---

  if (!isPlacement || !dragRect) return null;

  // Compute the screen-space rectangle for rendering
  const left = Math.min(dragRect.originScreen.x, dragRect.currentScreen.x);
  const top = Math.min(dragRect.originScreen.y, dragRect.currentScreen.y);
  const screenWidth = Math.abs(dragRect.currentScreen.x - dragRect.originScreen.x);
  const screenHeight = Math.abs(dragRect.currentScreen.y - dragRect.originScreen.y);

  // Compute canvas-space dimensions for the tooltip
  const originCanvas = screenToCanvas(dragRect.originScreen, viewport);
  const currentCanvas = screenToCanvas(dragRect.currentScreen, viewport);
  const canvasWidth = Math.max(Math.round(Math.abs(currentCanvas.x - originCanvas.x)), MIN_OBJECT_WIDTH);
  const canvasHeight = Math.max(Math.round(Math.abs(currentCanvas.y - originCanvas.y)), MIN_OBJECT_HEIGHT);

  // Only show the rectangle if we've exceeded the drag threshold
  const rawCanvasW = Math.abs(currentCanvas.x - originCanvas.x);
  const rawCanvasH = Math.abs(currentCanvas.y - originCanvas.y);
  const showRect = rawCanvasW >= DRAG_THRESHOLD || rawCanvasH >= DRAG_THRESHOLD;

  if (!showRect) return null;

  // Determine if we're placing a shape (render shape preview) or service (render generic rect)
  const isPlaceShape = typeof activeTool === 'object' && activeTool.type === 'place-shape';
  const shape: GeometricShape = isPlaceShape
    ? (activeTool as { type: 'place-shape'; shape: string }).shape as GeometricShape
    : 'rectangle';

  const { borderColor, borderWidth: bw, fill, fillColor } = DEFAULT_GEO_VISUAL;
  const borderRadius = shape === 'ellipse' ? '50%' : '0px';

  return (
    <>
      {/* Sizing preview */}
      <div
        data-testid="drag-sizing-rect"
        style={{
          position: 'absolute',
          left: `${left}px`,
          top: `${top}px`,
          width: `${screenWidth}px`,
          height: `${screenHeight}px`,
          ...(isPlaceShape
            ? {
                border: `${bw}px solid ${borderColor}`,
                borderRadius,
                backgroundColor: fill ? fillColor : 'transparent',
                opacity: 0.8,
              }
            : {
                border: '2px dashed rgba(59, 130, 246, 0.8)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
              }),
          pointerEvents: 'none',
          boxSizing: 'border-box',
          zIndex: 9999,
        }}
      />
      {/* Dimension tooltip — positioned inside the drag rect to avoid overflow */}
      <div
        data-testid="drag-sizing-tooltip"
        style={{
          position: 'absolute',
          left: `${left + screenWidth - 80}px`,
          top: `${top + screenHeight - 28}px`,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          color: '#fff',
          padding: '2px 6px',
          borderRadius: '4px',
          fontSize: '12px',
          whiteSpace: 'nowrap',
          pointerEvents: 'none',
          zIndex: 10000,
        }}
      >
        {canvasWidth} × {canvasHeight}
      </div>
    </>
  );
}
