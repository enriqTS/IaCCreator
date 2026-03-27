'use client';

import { useCallback, useRef } from 'react';
import { MIN_PANEL_HEIGHT, MAX_PANEL_HEIGHT_RATIO } from '@/components/config/panel-constants';

interface ResizeHandleProps {
  onResize: (newHeight: number) => void;
  onCollapseThreshold: () => void;
}

export default function ResizeHandle({ onResize, onCollapseThreshold }: ResizeHandleProps) {
  const isDragging = useRef(false);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging.current) return;
      const rawHeight = window.innerHeight - e.clientY;
      if (rawHeight < MIN_PANEL_HEIGHT) {
        onCollapseThreshold();
        return;
      }
      const maxHeight = MAX_PANEL_HEIGHT_RATIO * window.innerHeight;
      const clampedHeight = Math.min(Math.max(rawHeight, MIN_PANEL_HEIGHT), maxHeight);
      onResize(clampedHeight);
    },
    [onResize, onCollapseThreshold],
  );

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  }, [handleMouseMove]);

  const handleMouseDown = useCallback(() => {
    isDragging.current = true;
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [handleMouseMove, handleMouseUp]);

  return (
    <div
      data-testid="resize-handle"
      onMouseDown={handleMouseDown}
      style={{
        height: 6,
        cursor: 'ns-resize',
        backgroundColor: 'transparent',
        position: 'relative',
        zIndex: 1,
      }}
    />
  );
}
