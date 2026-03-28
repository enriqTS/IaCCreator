'use client';

import { useRef, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { SHAPE_PATH_REGISTRY } from '@/utils/shape-paths';
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

  const isDragging = useRef(false);
  const didDrag = useRef(false);
  const lastMouse = useRef<{ x: number; y: number } | null>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;

    // In placement mode, let the DragSizingOverlay handle the mousedown instead
    const tool = useDiagramStore.getState().activeTool;
    if (typeof tool === 'object' && (tool.type === 'place-service' || tool.type === 'place-shape')) return;

    // Locked: allow selection but prevent drag
    if (object.locked) {
      e.stopPropagation();
      if (e.shiftKey) {
        toggleObjectSelection(object.id);
      } else {
        selectObject(object.id);
      }
      return;
    }

    e.stopPropagation();
    useDiagramStore.getState().beginDragGesture();

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
  }, [object.id, object.locked, isSelected, selectObject, toggleObjectSelection, moveSelectedObjects]);

  // Get SVG path from registry, fall back to rectangle
  const pathFn = SHAPE_PATH_REGISTRY[shape] ?? SHAPE_PATH_REGISTRY['rectangle'];
  const pathD = pathFn(width, height);

  const strokeColor = isSelected ? 'rgba(59, 130, 246, 0.8)' : borderColor;
  const fillValue = fill ? fillColor : 'transparent';
  const strokeHitWidth = Math.max(borderWidth, MIN_STROKE_HIT_WIDTH);

  return (
    <div
      data-testid={`geometric-object-${object.id}`}
      data-object-id={object.id}
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
      {object.locked && (
        <span
          data-testid={`lock-badge-${object.id}`}
          style={{
            position: 'absolute',
            top: 2,
            right: 2,
            fontSize: '10px',
            lineHeight: 1,
            pointerEvents: 'none',
            zIndex: 1,
          }}
        >
          🔒
        </span>
      )}
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ position: 'absolute', inset: 0, overflow: 'visible' }}
      >
        {/* Invisible wider hit area for easier clicking */}
        <path
          d={pathD}
          fill={fill ? 'transparent' : 'none'}
          stroke="transparent"
          strokeWidth={strokeHitWidth}
          onMouseDown={handleMouseDown}
          style={{ pointerEvents: fill ? 'fill' : 'stroke', cursor: object.locked ? 'not-allowed' : 'grab' }}
        />
        {/* Visible shape */}
        <path
          d={pathD}
          fill={fillValue}
          stroke={strokeColor}
          strokeWidth={borderWidth}
          style={{ pointerEvents: fill ? 'auto' : 'none' }}
          onMouseDown={fill ? handleMouseDown : undefined}
        />
      </svg>
    </div>
  );
}
