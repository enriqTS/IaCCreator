'use client';

import { useRef, useCallback, useState, useEffect } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import type { TextObject } from '@/types/diagram';

interface TextObjectComponentProps {
  object: TextObject;
  isSelected: boolean;
}

/** Measure text dimensions using an offscreen canvas. */
function measureText(
  text: string,
  fontSize: number,
  bold: boolean,
  italic: boolean,
): { width: number; height: number } {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) return { width: 50, height: fontSize + 8 };

  const style = `${italic ? 'italic ' : ''}${bold ? 'bold ' : ''}${fontSize}px sans-serif`;
  ctx.font = style;

  const lines = (text || ' ').split('\n');
  let maxWidth = 0;
  for (const line of lines) {
    const m = ctx.measureText(line || ' ');
    if (m.width > maxWidth) maxWidth = m.width;
  }

  const padding = 16; // 4px padding on each side * 2 + some breathing room
  const lineHeight = fontSize * 1.4;
  return {
    width: Math.ceil(maxWidth) + padding,
    height: Math.ceil(lines.length * lineHeight) + padding,
  };
}

export default function TextObjectComponent({ object, isSelected }: TextObjectComponentProps) {
  const selectObject = useDiagramStore((s) => s.selectObject);
  const toggleObjectSelection = useDiagramStore((s) => s.toggleObjectSelection);
  const moveSelectedObjects = useDiagramStore((s) => s.moveSelectedObjects);
  const editingTextId = useDiagramStore((s) => s.editingTextId);
  const setEditingTextId = useDiagramStore((s) => s.setEditingTextId);
  const updateTextContent = useDiagramStore((s) => s.updateTextContent);

  const { width, height, fontSize, fontColor, textAlign, bold, italic } = object.visualConfig;

  const isEditing = editingTextId === object.id;
  const [editValue, setEditValue] = useState(object.content);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isDragging = useRef(false);
  const didDrag = useRef(false);
  const lastMouse = useRef<{ x: number; y: number } | null>(null);

  // Auto-size the box to fit the text content
  const prevSizeRef = useRef<{ w: number; h: number } | null>(null);
  useEffect(() => {
    const text = isEditing ? editValue : object.content;
    if (!text) return;
    const { fontSize: fs, bold: b, italic: it } = object.visualConfig;
    const measured = measureText(text, fs, b, it);
    // Clamp to the same minimums the store uses (40x40)
    const targetW = Math.max(measured.width, 40);
    const targetH = Math.max(measured.height, 40);
    const prev = prevSizeRef.current;
    if (!prev || Math.abs(targetW - prev.w) > 0.5 || Math.abs(targetH - prev.h) > 0.5) {
      prevSizeRef.current = { w: targetW, h: targetH };
      useDiagramStore.getState().updateObjectBounds(object.id, { width: targetW, height: targetH });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [object.content, object.id, isEditing, editValue, fontSize, bold, italic]);

  // Focus textarea when entering edit mode
  useEffect(() => {
    if (isEditing && textareaRef.current) {
      setEditValue(object.content);
      textareaRef.current.focus();
      textareaRef.current.select();
    }
  }, [isEditing, object.content]);

  const commitEdit = useCallback(() => {
    setEditingTextId(null);
    updateTextContent(object.id, editValue);
  }, [object.id, editValue, setEditingTextId, updateTextContent]);

  const handleDoubleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (object.locked) return;
    setEditingTextId(object.id);
  }, [object.id, object.locked, setEditingTextId]);

  const handleBlur = useCallback(() => {
    commitEdit();
  }, [commitEdit]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setEditingTextId(null);
    }
  }, [setEditingTextId]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    if (isEditing) return; // Don't start drag while editing

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
  }, [object.id, object.locked, isSelected, isEditing, selectObject, toggleObjectSelection, moveSelectedObjects]);

  const borderStyle = isSelected
    ? '2px solid rgba(59, 130, 246, 0.8)'
    : '2px solid transparent';

  return (
    <div
      data-testid={`text-object-${object.id}`}
      data-object-id={object.id}
      onMouseDown={handleMouseDown}
      onDoubleClick={handleDoubleClick}
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        transform: `translate(${object.position.x - width / 2}px, ${object.position.y - height / 2}px)`,
        width: `${width}px`,
        height: `${height}px`,
        pointerEvents: 'auto',
        cursor: object.locked ? 'not-allowed' : isEditing ? 'text' : 'grab',
        userSelect: isEditing ? 'text' : 'none',
        border: borderStyle,
        borderRadius: '2px',
        boxSizing: 'border-box',
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
          }}
        >
          🔒
        </span>
      )}
      {isEditing ? (
        <textarea
          ref={textareaRef}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          style={{
            width: '100%',
            height: '100%',
            fontSize: `${fontSize}px`,
            color: fontColor,
            textAlign,
            fontWeight: bold ? 'bold' : 'normal',
            fontStyle: italic ? 'italic' : 'normal',
            background: 'transparent',
            border: 'none',
            outline: 'none',
            resize: 'none',
            padding: '4px',
            boxSizing: 'border-box',
            fontFamily: 'sans-serif',
            overflow: 'hidden',
          }}
        />
      ) : (
        <div
          style={{
            width: '100%',
            height: '100%',
            fontSize: `${fontSize}px`,
            color: fontColor,
            textAlign,
            fontWeight: bold ? 'bold' : 'normal',
            fontStyle: italic ? 'italic' : 'normal',
            padding: '4px',
            boxSizing: 'border-box',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: 'sans-serif',
          }}
        >
          {object.content}
        </div>
      )}
    </div>
  );
}
