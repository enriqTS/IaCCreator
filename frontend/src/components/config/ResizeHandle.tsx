'use client';

import { useCallback, useRef, useEffect } from 'react';
import { MIN_PANEL_HEIGHT, MAX_PANEL_HEIGHT_RATIO } from '@/components/config/panel-constants';

interface ResizeHandleProps {
  onResize: (newHeight: number) => void;
  onCollapseThreshold: () => void;
  /** Called when dragging back above the collapse threshold after collapsing */
  onExpandFromDrag?: (height: number) => void;
}

export default function ResizeHandle({ onResize, onCollapseThreshold, onExpandFromDrag }: ResizeHandleProps) {
  const isDragging = useRef(false);
  const isCollapsed = useRef(false);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging.current) return;
      e.preventDefault();
      const rawHeight = window.innerHeight - e.clientY;
      const maxHeight = MAX_PANEL_HEIGHT_RATIO * window.innerHeight;

      if (rawHeight < MIN_PANEL_HEIGHT) {
        if (!isCollapsed.current) {
          isCollapsed.current = true;
          onCollapseThreshold();
        }
        // Keep dragging active — don't stop listening
        return;
      }

      // If we were collapsed and dragged back up, re-expand
      if (isCollapsed.current) {
        isCollapsed.current = false;
        const clampedHeight = Math.min(Math.max(rawHeight, MIN_PANEL_HEIGHT), maxHeight);
        if (onExpandFromDrag) {
          onExpandFromDrag(clampedHeight);
        }
        return;
      }

      const clampedHeight = Math.min(Math.max(rawHeight, MIN_PANEL_HEIGHT), maxHeight);
      onResize(clampedHeight);
    },
    [onResize, onCollapseThreshold, onExpandFromDrag],
  );

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
    isCollapsed.current = false;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, [handleMouseMove]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      isDragging.current = true;
      isCollapsed.current = false;
      document.body.style.cursor = 'ns-resize';
      document.body.style.userSelect = 'none';
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [handleMouseMove, handleMouseUp],
  );

  // Cleanup on unmount — keep listeners alive even if component unmounts during drag
  useEffect(() => {
    return () => {
      if (isDragging.current) {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };
  }, [handleMouseMove, handleMouseUp]);

  return (
    <div
      data-testid="resize-handle"
      onMouseDown={handleMouseDown}
      style={{
        height: 14,
        cursor: 'ns-resize',
        backgroundColor: 'transparent',
        position: 'relative',
        zIndex: 10,
        marginTop: -4,
      }}
    />
  );
}
