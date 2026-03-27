'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { getObjectBounds } from '@/types/diagram';
import { canvasToScreen } from '@/utils/viewport';

interface InlineRenameOverlayProps {
  objectId: string;
  onClose: () => void;
}

export default function InlineRenameOverlay({ objectId, onClose }: InlineRenameOverlayProps) {
  const obj = useDiagramStore((s) => s.canvasObjects.get(objectId));
  const viewport = useDiagramStore((s) => s.viewport);
  const updateCanvasObject = useDiagramStore((s) => s.updateCanvasObject);

  const originalName = obj?.name ?? '';
  const [value, setValue] = useState(originalName);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus and select all text on mount
  useEffect(() => {
    const input = inputRef.current;
    if (input) {
      input.focus();
      input.select();
    }
  }, []);

  const commit = useCallback(() => {
    const trimmed = value.trim();
    if (trimmed && trimmed !== originalName) {
      updateCanvasObject(objectId, { name: trimmed } as Partial<typeof obj & { name: string }>);
    }
    onClose();
  }, [value, originalName, objectId, updateCanvasObject, onClose]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      commit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  }, [commit, onClose]);

  if (!obj) return null;

  // Compute screen-space bounding box
  const bounds = getObjectBounds(obj);
  const topLeft = canvasToScreen({ x: bounds.x, y: bounds.y }, viewport);
  const bottomRight = canvasToScreen({ x: bounds.x + bounds.width, y: bounds.y + bounds.height }, viewport);
  const screenWidth = Math.max(bottomRight.x - topLeft.x, 100);
  const screenHeight = Math.max(bottomRight.y - topLeft.y, 30);

  return (
    <div
      data-testid="inline-rename-overlay"
      style={{
        position: 'absolute',
        left: topLeft.x,
        top: topLeft.y,
        width: screenWidth,
        height: screenHeight,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 2000,
        pointerEvents: 'auto',
      }}
    >
      <input
        ref={inputRef}
        data-testid="inline-rename-input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={commit}
        style={{
          width: '90%',
          padding: '4px 8px',
          fontSize: '13px',
          color: '#ffffff',
          backgroundColor: '#1e1e1e',
          border: '1px solid #3b82f6',
          borderRadius: '4px',
          outline: 'none',
          textAlign: 'center',
        }}
      />
    </div>
  );
}
