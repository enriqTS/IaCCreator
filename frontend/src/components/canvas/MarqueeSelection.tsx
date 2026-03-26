'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { screenToCanvas } from '@/utils/viewport';
import { getObjectBounds } from '@/types/diagram';
import type { Point, Rect } from '@/types/diagram';

interface MarqueeSelectionProps {
  containerRef: React.RefObject<HTMLDivElement | null>;
}

/** Check if two axis-aligned rectangles intersect */
function rectsIntersect(a: Rect, b: Rect): boolean {
  return (
    a.x < b.x + b.width &&
    a.x + a.width > b.x &&
    a.y < b.y + b.height &&
    a.y + a.height > b.y
  );
}

export default function MarqueeSelection({ containerRef }: MarqueeSelectionProps) {
  const activeTool = useDiagramStore((s) => s.activeTool);
  const viewport = useDiagramStore((s) => s.viewport);

  const isDragging = useRef(false);
  const originScreen = useRef<Point | null>(null);

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

  useEffect(() => {
    if (activeTool !== 'pointer') {
      isDragging.current = false;
      originScreen.current = null;
      setDragRect(null);
      return;
    }

    const container = containerRef.current;
    if (!container) return;

    const handleMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return;

      // Only start marquee on empty canvas (the container itself or the background canvas element)
      const target = e.target as HTMLElement;
      const isEmptyCanvas = target === container || target.tagName === 'CANVAS';
      if (!isEmptyCanvas) return;

      const offset = getContainerOffset();
      if (!offset) return;

      const screenPt: Point = { x: e.clientX - offset.x, y: e.clientY - offset.y };
      isDragging.current = true;
      originScreen.current = screenPt;
      setDragRect({ originScreen: screenPt, currentScreen: screenPt });
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

      const currentViewport = useDiagramStore.getState().viewport;

      const originCanvas = screenToCanvas(origin, currentViewport);
      const endCanvas = screenToCanvas(endScreen, currentViewport);

      const minX = Math.min(originCanvas.x, endCanvas.x);
      const minY = Math.min(originCanvas.y, endCanvas.y);
      const width = Math.abs(endCanvas.x - originCanvas.x);
      const height = Math.abs(endCanvas.y - originCanvas.y);

      // Only perform marquee selection if there was meaningful drag
      if (width > 2 || height > 2) {
        const rect: Rect = { x: minX, y: minY, width, height };
        useDiagramStore.getState().selectObjectsByRect(rect);
      }

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
  }, [activeTool, containerRef, getContainerOffset]);

  // --- Highlight intersected objects during drag ---
  const highlightedIds = useHighlightedObjects(dragRect, viewport);

  if (activeTool !== 'pointer' || !dragRect) return null;

  const left = Math.min(dragRect.originScreen.x, dragRect.currentScreen.x);
  const top = Math.min(dragRect.originScreen.y, dragRect.currentScreen.y);
  const screenWidth = Math.abs(dragRect.currentScreen.x - dragRect.originScreen.x);
  const screenHeight = Math.abs(dragRect.currentScreen.y - dragRect.originScreen.y);

  // Don't render until there's a visible drag
  if (screenWidth < 2 && screenHeight < 2) return null;

  return (
    <>
      {/* Marquee selection rectangle */}
      <div
        data-testid="marquee-selection-rect"
        style={{
          position: 'absolute',
          left: `${left}px`,
          top: `${top}px`,
          width: `${screenWidth}px`,
          height: `${screenHeight}px`,
          border: '1px solid rgba(59, 130, 246, 0.8)',
          backgroundColor: 'rgba(59, 130, 246, 0.15)',
          pointerEvents: 'none',
          zIndex: 10,
        }}
      />
      {/* Highlight overlays on intersected objects */}
      {highlightedIds.map((id) => (
        <MarqueeHighlight key={id} objectId={id} viewport={viewport} />
      ))}
    </>
  );
}

/** Hook that computes which object IDs intersect the current marquee rect */
function useHighlightedObjects(
  dragRect: { originScreen: Point; currentScreen: Point } | null,
  viewport: { offsetX: number; offsetY: number; scale: number },
): string[] {
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);

  if (!dragRect) return [];

  const originCanvas = screenToCanvas(dragRect.originScreen, viewport);
  const currentCanvas = screenToCanvas(dragRect.currentScreen, viewport);

  const minX = Math.min(originCanvas.x, currentCanvas.x);
  const minY = Math.min(originCanvas.y, currentCanvas.y);
  const marqueeRect: Rect = {
    x: minX,
    y: minY,
    width: Math.abs(currentCanvas.x - originCanvas.x),
    height: Math.abs(currentCanvas.y - originCanvas.y),
  };

  const ids: string[] = [];
  for (const obj of canvasObjects.values()) {
    const bounds = getObjectBounds(obj);
    if (rectsIntersect(marqueeRect, bounds)) {
      ids.push(obj.id);
    }
  }
  return ids;
}

/** Renders a highlight overlay for a single object during marquee drag */
function MarqueeHighlight({
  objectId,
  viewport,
}: {
  objectId: string;
  viewport: { offsetX: number; offsetY: number; scale: number };
}) {
  const obj = useDiagramStore((s) => s.canvasObjects.get(objectId));
  if (!obj) return null;

  const bounds = getObjectBounds(obj);

  // Convert canvas-space bounds to screen-space for the overlay
  const screenX = bounds.x * viewport.scale + viewport.offsetX;
  const screenY = bounds.y * viewport.scale + viewport.offsetY;
  const screenW = bounds.width * viewport.scale;
  const screenH = bounds.height * viewport.scale;

  return (
    <div
      data-testid={`marquee-highlight-${objectId}`}
      style={{
        position: 'absolute',
        left: `${screenX}px`,
        top: `${screenY}px`,
        width: `${screenW}px`,
        height: `${screenH}px`,
        border: '2px solid rgba(59, 130, 246, 0.6)',
        backgroundColor: 'rgba(59, 130, 246, 0.08)',
        borderRadius: '2px',
        pointerEvents: 'none',
        zIndex: 9,
      }}
    />
  );
}
