'use client';

import { useRef, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import type { LineObject } from '@/types/diagram';

interface LineObjectComponentProps {
  line: LineObject;
  isSelected: boolean;
}

export default function LineObjectComponent({ line, isSelected }: LineObjectComponentProps) {
  const selectObject = useDiagramStore((s) => s.selectObject);
  const toggleObjectSelection = useDiagramStore((s) => s.toggleObjectSelection);
  const moveSelectedObjects = useDiagramStore((s) => s.moveSelectedObjects);

  const { color, borderWidth, strokeStyle, startArrow, endArrow } = line.visualConfig;

  const markerId = `line-${line.id}`;
  const startMarkerId = `${markerId}-start`;
  const endMarkerId = `${markerId}-end`;

  const dashArray = strokeStyle === 'dashed' ? `${borderWidth * 3} ${borderWidth * 2}` : undefined;

  // Arrowhead size scales with stroke width
  const arrowSize = Math.max(borderWidth * 3, 6);

  const isDragging = useRef(false);
  const didDrag = useRef(false);
  const lastMouse = useRef<{ x: number; y: number } | null>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent<SVGLineElement>) => {
    if (e.button !== 0) return;

    // In placement mode, let the DragSizingOverlay handle the mousedown instead
    const tool = useDiagramStore.getState().activeTool;
    if (typeof tool === 'object' && (tool.type === 'place-service' || tool.type === 'place-shape')) return;

    // Locked: allow selection but prevent drag
    if (line.locked) {
      e.stopPropagation();
      if (e.shiftKey) {
        toggleObjectSelection(line.id);
      } else {
        selectObject(line.id);
      }
      return;
    }

    e.stopPropagation();
    useDiagramStore.getState().beginDragGesture();

    if (!e.shiftKey && !isSelected) {
      selectObject(line.id);
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
          toggleObjectSelection(line.id);
        } else {
          selectObject(line.id);
        }
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  }, [line.id, line.locked, isSelected, selectObject, toggleObjectSelection, moveSelectedObjects]);

  // Compute midpoint for lock indicator
  const midX = (line.start.x + line.end.x) / 2;
  const midY = (line.start.y + line.end.y) / 2;

  return (
    <g data-testid={`line-object-${line.id}`} data-object-id={line.id} style={{ pointerEvents: 'auto', cursor: line.locked ? 'not-allowed' : 'pointer' }}>
      <defs>
        {startArrow && (
          <marker
            id={startMarkerId}
            markerWidth={arrowSize}
            markerHeight={arrowSize}
            refX={arrowSize}
            refY={arrowSize / 2}
            orient="auto-start-reverse"
            markerUnits="userSpaceOnUse"
          >
            <path
              d={`M ${arrowSize} 0 L 0 ${arrowSize / 2} L ${arrowSize} ${arrowSize}`}
              fill="none"
              stroke={color}
              strokeWidth={Math.max(borderWidth * 0.6, 1)}
            />
          </marker>
        )}
        {endArrow && (
          <marker
            id={endMarkerId}
            markerWidth={arrowSize}
            markerHeight={arrowSize}
            refX={0}
            refY={arrowSize / 2}
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <path
              d={`M 0 0 L ${arrowSize} ${arrowSize / 2} L 0 ${arrowSize}`}
              fill="none"
              stroke={color}
              strokeWidth={Math.max(borderWidth * 0.6, 1)}
            />
          </marker>
        )}
      </defs>

      {/* Invisible wider hit area for easier clicking */}
      <line
        x1={line.start.x}
        y1={line.start.y}
        x2={line.end.x}
        y2={line.end.y}
        stroke="transparent"
        strokeWidth={Math.max(borderWidth + 10, 12)}
        onMouseDown={handleMouseDown}
      />

      {/* Selection highlight glow */}
      {isSelected && (
        <line
          x1={line.start.x}
          y1={line.start.y}
          x2={line.end.x}
          y2={line.end.y}
          stroke="rgba(59, 130, 246, 0.5)"
          strokeWidth={borderWidth + 6}
          strokeLinecap="round"
        />
      )}

      {/* Main visible line */}
      <line
        x1={line.start.x}
        y1={line.start.y}
        x2={line.end.x}
        y2={line.end.y}
        stroke={color}
        strokeWidth={borderWidth}
        strokeDasharray={dashArray}
        strokeLinecap="round"
        markerStart={startArrow ? `url(#${startMarkerId})` : undefined}
        markerEnd={endArrow ? `url(#${endMarkerId})` : undefined}
      />

      {/* Lock indicator at midpoint */}
      {line.locked && (
        <text
          data-testid={`lock-badge-${line.id}`}
          x={midX}
          y={midY - 8}
          textAnchor="middle"
          fontSize="12"
          style={{ pointerEvents: 'none', userSelect: 'none' }}
        >
          🔒
        </text>
      )}
    </g>
  );
}
