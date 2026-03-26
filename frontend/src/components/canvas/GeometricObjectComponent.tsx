'use client';

import { useRef, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import type { GeometricObject } from '@/types/diagram';

interface GeometricObjectComponentProps {
  object: GeometricObject;
  isSelected: boolean;
}

/** Minimum clickable stroke width for hollow objects (px) */
const MIN_STROKE_HIT_WIDTH = 8;

export default function GeometricObjectComponent({ object, isSelected }: GeometricObjectComponentProps) {
  const selectObject = useDiagramStore((s) => s.selectObject);
  const toggleObjectSelection = useDiagramStore((s) => s.toggleObjectSelection);
  const moveSelectedObjects = useDiagramStore((s) => s.moveSelectedObjects);

  const { width, height, fill, fillColor, borderColor, borderWidth, shape } = object.visualConfig;

  const backgroundColor = fill ? fillColor : 'transparent';
  const borderRadius = shape === 'ellipse' ? '50%' : '0px';

  const borderStyle = isSelected
    ? `${borderWidth}px solid rgba(59, 130, 246, 0.8)`
    : `${borderWidth}px solid ${borderColor}`;

  const isDragging = useRef(false);
  const didDrag = useRef(false);
  const lastMouse = useRef<{ x: number; y: number } | null>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;

    // In placement mode, let the DragSizingOverlay handle the mousedown instead
    const tool = useDiagramStore.getState().activeTool;
    if (typeof tool === 'object' && (tool.type === 'place-service' || tool.type === 'place-shape')) return;

    e.stopPropagation();

    if (!e.shiftKey && !isSelected) {
      selectObject(object.id);
    }

    isDragging.current = true;
    didDrag.current = false;
    lastMouse.current = { x: e.clientX, y: e.clientY };

    const viewport = useDiagramStore.getState().viewport;

    const handleMouseMove = (ev: MouseEvent) => {
      if (!isDragging.current || !lastMouse.current) return;
      const dx = (ev.clientX - lastMouse.current.x) / viewport.scale;
      const dy = (ev.clientY - lastMouse.current.y) / viewport.scale;
      lastMouse.current = { x: ev.clientX, y: ev.clientY };
      if (Math.abs(dx) > 0 || Math.abs(dy) > 0) {
        didDrag.current = true;
        moveSelectedObjects(dx, dy);
      }
    };

    const handleMouseUp = (ev: MouseEvent) => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      isDragging.current = false;
      lastMouse.current = null;

      if (!didDrag.current) {
        if (ev.shiftKey) {
          toggleObjectSelection(object.id);
        } else {
          selectObject(object.id);
        }
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  }, [object.id, isSelected, selectObject, toggleObjectSelection, moveSelectedObjects]);

  // When filled, the entire area captures pointer events — single div is sufficient
  if (fill) {
    return (
      <div
        data-testid={`geometric-object-${object.id}`}
        onMouseDown={handleMouseDown}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          transform: `translate(${object.position.x - width / 2}px, ${object.position.y - height / 2}px)`,
          width: `${width}px`,
          height: `${height}px`,
          backgroundColor,
          border: borderStyle,
          borderRadius,
          boxSizing: 'border-box',
          pointerEvents: 'auto',
          cursor: 'grab',
          userSelect: 'none',
        }}
      />
    );
  }

  // Hollow (fill: false) — interior is transparent to pointer events,
  // border-only overlay captures clicks with a minimum 8px hit area.
  const strokeHitWidth = Math.max(borderWidth, MIN_STROKE_HIT_WIDTH);

  return (
    <div
      data-testid={`geometric-object-${object.id}`}
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        transform: `translate(${object.position.x - width / 2}px, ${object.position.y - height / 2}px)`,
        width: `${width}px`,
        height: `${height}px`,
        pointerEvents: 'none',
        userSelect: 'none',
      }}
    >
      {/* Visual interior — renders the visible border but does not capture events */}
      <div
        data-testid={`geometric-interior-${object.id}`}
        style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'transparent',
          border: borderStyle,
          borderRadius,
          boxSizing: 'border-box',
          pointerEvents: 'none',
        }}
      />
      {/* Border-only hit overlay — captures pointer events on the stroke area */}
      <div
        data-testid={`geometric-border-overlay-${object.id}`}
        onMouseDown={handleMouseDown}
        style={{
          position: 'absolute',
          inset: `-${strokeHitWidth / 2}px`,
          borderRadius,
          border: `${strokeHitWidth}px solid transparent`,
          boxSizing: 'border-box',
          pointerEvents: 'auto',
          cursor: 'grab',
        }}
      />
    </div>
  );
}
