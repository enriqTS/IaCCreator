'use client';

import { useMemo, useRef, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { getObjectBounds } from '@/types/diagram';
import type { Rect } from '@/types/diagram';

/** Minimap dimensions in pixels. */
const MINIMAP_WIDTH = 180;
const MINIMAP_HEIGHT = 120;
const MINIMAP_PADDING = 8;

/**
 * Minimap component — shows a small overview of the entire canvas
 * with a draggable viewport rectangle for navigation.
 *
 * Positioned in the bottom-right corner of the canvas area.
 */
export default function Minimap() {
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const viewport = useDiagramStore((s) => s.viewport);
  const pan = useDiagramStore((s) => s.pan);

  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  // Compute the bounding box of all objects
  const contentBounds = useMemo((): Rect | null => {
    if (canvasObjects.size === 0) return null;

    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

    for (const obj of canvasObjects.values()) {
      const bounds = getObjectBounds(obj);
      minX = Math.min(minX, bounds.x);
      minY = Math.min(minY, bounds.y);
      maxX = Math.max(maxX, bounds.x + bounds.width);
      maxY = Math.max(maxY, bounds.y + bounds.height);
    }

    // Add padding around content
    const pad = 50;
    return {
      x: minX - pad,
      y: minY - pad,
      width: maxX - minX + pad * 2,
      height: maxY - minY + pad * 2,
    };
  }, [canvasObjects]);

  // Compute the minimap scale and transform
  const minimapTransform = useMemo(() => {
    if (!contentBounds) return null;

    const innerW = MINIMAP_WIDTH - MINIMAP_PADDING * 2;
    const innerH = MINIMAP_HEIGHT - MINIMAP_PADDING * 2;

    const scaleX = innerW / contentBounds.width;
    const scaleY = innerH / contentBounds.height;
    const scale = Math.min(scaleX, scaleY);

    // Center the content within the minimap
    const scaledW = contentBounds.width * scale;
    const scaledH = contentBounds.height * scale;
    const offsetX = MINIMAP_PADDING + (innerW - scaledW) / 2;
    const offsetY = MINIMAP_PADDING + (innerH - scaledH) / 2;

    return { scale, offsetX, offsetY };
  }, [contentBounds]);

  // Compute object rectangles in minimap space
  const objectRects = useMemo(() => {
    if (!contentBounds || !minimapTransform) return [];

    const rects: Array<{ x: number; y: number; w: number; h: number; color: string }> = [];

    for (const obj of canvasObjects.values()) {
      if (obj.objectType === 'line') continue; // Skip lines for clarity

      const bounds = getObjectBounds(obj);
      const x = (bounds.x - contentBounds.x) * minimapTransform.scale + minimapTransform.offsetX;
      const y = (bounds.y - contentBounds.y) * minimapTransform.scale + minimapTransform.offsetY;
      const w = Math.max(2, bounds.width * minimapTransform.scale);
      const h = Math.max(2, bounds.height * minimapTransform.scale);

      let color = '#6b7280'; // neutral gray default
      if (obj.objectType === 'architecture-block') color = '#f59e0b';
      else if (obj.objectType === 'geometric') color = '#8b5cf6';
      else if (obj.objectType === 'text') color = '#6b7280';
      else if (obj.objectType === 'uml') color = '#3b82f6';

      rects.push({ x, y, w, h, color });
    }

    return rects;
  }, [canvasObjects, contentBounds, minimapTransform]);

  // Compute the viewport rectangle in minimap space
  const viewportRect = useMemo(() => {
    if (!contentBounds || !minimapTransform) return null;

    // The visible area in canvas coordinates
    const visibleLeft = -viewport.offsetX / viewport.scale;
    const visibleTop = -viewport.offsetY / viewport.scale;
    const visibleWidth = window.innerWidth / viewport.scale;
    const visibleHeight = window.innerHeight / viewport.scale;

    // Transform to minimap space
    const x = (visibleLeft - contentBounds.x) * minimapTransform.scale + minimapTransform.offsetX;
    const y = (visibleTop - contentBounds.y) * minimapTransform.scale + minimapTransform.offsetY;
    const w = visibleWidth * minimapTransform.scale;
    const h = visibleHeight * minimapTransform.scale;

    return { x, y, w, h };
  }, [viewport, contentBounds, minimapTransform]);

  // Handle click/drag on minimap to navigate
  const navigateToMinimapPoint = useCallback((clientX: number, clientY: number) => {
    if (!contentBounds || !minimapTransform || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const mx = clientX - rect.left;
    const my = clientY - rect.top;

    // Convert minimap position to canvas coordinates
    const canvasX = (mx - minimapTransform.offsetX) / minimapTransform.scale + contentBounds.x;
    const canvasY = (my - minimapTransform.offsetY) / minimapTransform.scale + contentBounds.y;

    // Center the viewport on this canvas point
    const targetOffsetX = window.innerWidth / 2 - canvasX * viewport.scale;
    const targetOffsetY = window.innerHeight / 2 - canvasY * viewport.scale;

    const dx = targetOffsetX - viewport.offsetX;
    const dy = targetOffsetY - viewport.offsetY;
    pan(dx, dy);
  }, [contentBounds, minimapTransform, viewport, pan]);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    e.stopPropagation();
    e.preventDefault();
    isDragging.current = true;
    navigateToMinimapPoint(e.clientX, e.clientY);

    const handleMove = (ev: PointerEvent) => {
      if (!isDragging.current) return;
      navigateToMinimapPoint(ev.clientX, ev.clientY);
    };

    const handleUp = () => {
      isDragging.current = false;
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };

    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
  }, [navigateToMinimapPoint]);

  // Don't render if there's nothing on the canvas
  if (!contentBounds || !minimapTransform) return null;

  return (
    <div
      ref={containerRef}
      className="absolute bottom-4 right-4 z-50 rounded-lg border border-neutral-700 bg-neutral-900/90 backdrop-blur-sm shadow-lg overflow-hidden"
      style={{ width: MINIMAP_WIDTH, height: MINIMAP_HEIGHT, cursor: 'crosshair' }}
      onPointerDown={handlePointerDown}
      data-testid="minimap"
    >
      {/* Object representations */}
      <svg width={MINIMAP_WIDTH} height={MINIMAP_HEIGHT} className="absolute inset-0">
        {objectRects.map((r, i) => (
          <rect
            key={i}
            x={r.x}
            y={r.y}
            width={r.w}
            height={r.h}
            fill={r.color}
            opacity={0.7}
            rx={1}
          />
        ))}

        {/* Viewport rectangle */}
        {viewportRect && (
          <rect
            x={viewportRect.x}
            y={viewportRect.y}
            width={viewportRect.w}
            height={viewportRect.h}
            fill="rgba(59, 130, 246, 0.1)"
            stroke="rgba(59, 130, 246, 0.7)"
            strokeWidth={1.5}
            rx={2}
          />
        )}
      </svg>
    </div>
  );
}
