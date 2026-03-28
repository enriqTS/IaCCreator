'use client';

import { useRef, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import type { UMLObject } from '@/types/diagram';

interface UMLObjectComponentProps {
  object: UMLObject;
  isSelected: boolean;
}

export default function UMLObjectComponent({ object, isSelected }: UMLObjectComponentProps) {
  const selectObject = useDiagramStore((s) => s.selectObject);
  const toggleObjectSelection = useDiagramStore((s) => s.toggleObjectSelection);
  const moveSelectedObjects = useDiagramStore((s) => s.moveSelectedObjects);

  const { width, height, fillColor, borderColor, borderWidth, headerColor } = object.visualConfig;

  const isDragging = useRef(false);
  const didDrag = useRef(false);
  const lastMouse = useRef<{ x: number; y: number } | null>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;

    const tool = useDiagramStore.getState().activeTool;
    if (typeof tool === 'object' && (tool.type === 'place-service' || tool.type === 'place-shape')) return;

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

  const selectionBorder = isSelected
    ? `${borderWidth}px solid rgba(59, 130, 246, 0.8)`
    : `${borderWidth}px solid ${borderColor}`;

  const containerStyle: React.CSSProperties = {
    position: 'absolute',
    left: 0,
    top: 0,
    transform: `translate(${object.position.x - width / 2}px, ${object.position.y - height / 2}px)`,
    width: `${width}px`,
    height: `${height}px`,
    pointerEvents: 'auto',
    cursor: object.locked ? 'not-allowed' : 'grab',
    userSelect: 'none',
  };

  const lockBadge = object.locked ? (
    <span
      data-testid={`lock-badge-${object.id}`}
      style={{ position: 'absolute', top: 2, right: 2, fontSize: '10px', lineHeight: 1, pointerEvents: 'none' }}
    >
      🔒
    </span>
  ) : null;

  // --- Class / Interface ---
  if (object.umlKind === 'class' || object.umlKind === 'interface') {
    const stereotype = object.classData?.stereotype || (object.umlKind === 'interface' ? '«interface»' : '');
    const attrs = object.classData?.attributes ?? [];
    const methods = object.classData?.methods ?? [];
    const headerH = 36;

    return (
      <div data-testid={`uml-object-${object.id}`} data-object-id={object.id} onMouseDown={handleMouseDown} style={containerStyle}>
        {lockBadge}
        <div style={{ width: '100%', height: '100%', border: selectionBorder, boxSizing: 'border-box', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: fillColor }}>
          {/* Header */}
          <div style={{ background: headerColor, padding: '4px 8px', textAlign: 'center', minHeight: `${headerH}px`, flexShrink: 0 }}>
            {stereotype && <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.7)' }}>{stereotype}</div>}
            <div style={{ fontSize: '12px', color: '#fff', fontWeight: 'bold' }}>{object.name}</div>
          </div>
          {/* Attributes */}
          <div style={{ borderTop: `1px solid ${borderColor}`, padding: '4px 8px', flex: 1, overflow: 'hidden' }}>
            {attrs.map((a, i) => <div key={i} style={{ fontSize: '11px', color: '#ccc' }}>{a}</div>)}
          </div>
          {/* Methods */}
          <div style={{ borderTop: `1px solid ${borderColor}`, padding: '4px 8px', flex: 1, overflow: 'hidden' }}>
            {methods.map((m, i) => <div key={i} style={{ fontSize: '11px', color: '#ccc' }}>{m}</div>)}
          </div>
        </div>
      </div>
    );
  }

  // --- Actor ---
  if (object.umlKind === 'actor') {
    return (
      <div data-testid={`uml-object-${object.id}`} data-object-id={object.id} onMouseDown={handleMouseDown} style={containerStyle}>
        {lockBadge}
        {isSelected && <div style={{ position: 'absolute', inset: 0, border: '2px solid rgba(59, 130, 246, 0.8)', borderRadius: '4px', pointerEvents: 'none' }} />}
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
          {/* Head */}
          <circle cx={width / 2} cy={height * 0.18} r={height * 0.12} fill="none" stroke={borderColor} strokeWidth={borderWidth} />
          {/* Body */}
          <line x1={width / 2} y1={height * 0.3} x2={width / 2} y2={height * 0.58} stroke={borderColor} strokeWidth={borderWidth} />
          {/* Arms */}
          <line x1={width * 0.2} y1={height * 0.4} x2={width * 0.8} y2={height * 0.4} stroke={borderColor} strokeWidth={borderWidth} />
          {/* Left leg */}
          <line x1={width / 2} y1={height * 0.58} x2={width * 0.25} y2={height * 0.78} stroke={borderColor} strokeWidth={borderWidth} />
          {/* Right leg */}
          <line x1={width / 2} y1={height * 0.58} x2={width * 0.75} y2={height * 0.78} stroke={borderColor} strokeWidth={borderWidth} />
          {/* Name label */}
          <text x={width / 2} y={height * 0.95} textAnchor="middle" fontSize="11" fill={borderColor}>{object.name}</text>
        </svg>
      </div>
    );
  }

  // --- Use Case ---
  if (object.umlKind === 'use-case') {
    return (
      <div data-testid={`uml-object-${object.id}`} data-object-id={object.id} onMouseDown={handleMouseDown} style={containerStyle}>
        {lockBadge}
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
          <ellipse
            cx={width / 2} cy={height / 2} rx={width / 2 - borderWidth} ry={height / 2 - borderWidth}
            fill={fillColor} stroke={isSelected ? 'rgba(59, 130, 246, 0.8)' : borderColor} strokeWidth={borderWidth}
          />
          <text x={width / 2} y={height / 2} textAnchor="middle" dominantBaseline="central" fontSize="12" fill="#fff">{object.name}</text>
        </svg>
      </div>
    );
  }

  // --- Component ---
  if (object.umlKind === 'component') {
    const iconW = 16;
    const iconH = 12;
    const tabW = 8;
    const tabH = 4;
    return (
      <div data-testid={`uml-object-${object.id}`} data-object-id={object.id} onMouseDown={handleMouseDown} style={containerStyle}>
        {lockBadge}
        <div style={{ width: '100%', height: '100%', border: selectionBorder, boxSizing: 'border-box', background: fillColor, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {/* Component icon in top-right */}
          <svg width={iconW} height={iconH} style={{ position: 'absolute', top: 6, right: 6 }}>
            <rect x={0} y={0} width={iconW} height={iconH} fill="none" stroke={borderColor} strokeWidth={1} />
            <rect x={-tabW / 2} y={2} width={tabW} height={tabH} fill={fillColor} stroke={borderColor} strokeWidth={1} />
            <rect x={-tabW / 2} y={iconH - tabH - 2} width={tabW} height={tabH} fill={fillColor} stroke={borderColor} strokeWidth={1} />
          </svg>
          <span style={{ fontSize: '12px', color: '#fff' }}>{object.name}</span>
        </div>
      </div>
    );
  }

  // --- Package ---
  if (object.umlKind === 'package') {
    const tabW = Math.min(width * 0.4, 80);
    const tabH = 20;
    return (
      <div data-testid={`uml-object-${object.id}`} data-object-id={object.id} onMouseDown={handleMouseDown} style={containerStyle}>
        {lockBadge}
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
          {/* Tab */}
          <rect x={0} y={0} width={tabW} height={tabH} fill={headerColor} stroke={isSelected ? 'rgba(59, 130, 246, 0.8)' : borderColor} strokeWidth={borderWidth} />
          {/* Body */}
          <rect x={0} y={tabH} width={width} height={height - tabH} fill={fillColor} stroke={isSelected ? 'rgba(59, 130, 246, 0.8)' : borderColor} strokeWidth={borderWidth} />
          {/* Tab label */}
          <text x={tabW / 2} y={tabH / 2 + 4} textAnchor="middle" fontSize="10" fill="#fff">{object.name}</text>
        </svg>
      </div>
    );
  }

  // --- Node (3D box) ---
  if (object.umlKind === 'node') {
    const d = 12; // 3D depth offset
    return (
      <div data-testid={`uml-object-${object.id}`} data-object-id={object.id} onMouseDown={handleMouseDown} style={containerStyle}>
        {lockBadge}
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
          {/* Front face */}
          <rect x={0} y={d} width={width - d} height={height - d} fill={fillColor} stroke={isSelected ? 'rgba(59, 130, 246, 0.8)' : borderColor} strokeWidth={borderWidth} />
          {/* Top face */}
          <polygon points={`0,${d} ${d},0 ${width},0 ${width - d},${d}`} fill={headerColor} stroke={isSelected ? 'rgba(59, 130, 246, 0.8)' : borderColor} strokeWidth={borderWidth} />
          {/* Right face */}
          <polygon points={`${width - d},${d} ${width},0 ${width},${height - d} ${width - d},${height}`} fill={headerColor} stroke={isSelected ? 'rgba(59, 130, 246, 0.8)' : borderColor} strokeWidth={borderWidth} />
          {/* Name label */}
          <text x={(width - d) / 2} y={(height + d) / 2} textAnchor="middle" dominantBaseline="central" fontSize="12" fill="#fff">{object.name}</text>
        </svg>
      </div>
    );
  }

  // --- Fallback: generic rectangle with kind label ---
  return (
    <div data-testid={`uml-object-${object.id}`} data-object-id={object.id} onMouseDown={handleMouseDown} style={containerStyle}>
      {lockBadge}
      <div style={{ width: '100%', height: '100%', border: selectionBorder, boxSizing: 'border-box', background: fillColor, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
        <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>«{object.umlKind}»</span>
        <span style={{ fontSize: '12px', color: '#fff' }}>{object.name}</span>
      </div>
    </div>
  );
}
