'use client';

import { useRef, useEffect, useCallback } from 'react';
import { MIN_PANEL_HEIGHT, MAX_PANEL_HEIGHT_RATIO } from '@/components/config/panel-constants';

interface ResizeHandleProps {
  onResize: (newHeight: number) => void;
  onCollapseThreshold: () => void;
  onExpandFromDrag?: (height: number) => void;
}

export default function ResizeHandle({ onResize, onCollapseThreshold, onExpandFromDrag }: ResizeHandleProps) {
  const isDragging = useRef(false);
  const isCollapsed = useRef(false);
  const startY = useRef(0);
  const startHeight = useRef(0);

  // Store latest callbacks in refs so document listeners always use current versions
  const onResizeRef = useRef(onResize);
  const onCollapseRef = useRef(onCollapseThreshold);
  const onExpandRef = useRef(onExpandFromDrag);
  useEffect(() => {
    onResizeRef.current = onResize;
    onCollapseRef.current = onCollapseThreshold;
    onExpandRef.current = onExpandFromDrag;
  });

  // Stable handlers that never change identity — they read from refs
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging.current) return;
    e.preventDefault();

    const delta = startY.current - e.clientY;
    const rawHeight = startHeight.current + delta;
    const maxHeight = MAX_PANEL_HEIGHT_RATIO * window.innerHeight;

    if (rawHeight < MIN_PANEL_HEIGHT) {
      if (!isCollapsed.current) {
        isCollapsed.current = true;
        onCollapseRef.current();
      }
      return;
    }

    if (isCollapsed.current) {
      isCollapsed.current = false;
      const clamped = Math.min(Math.max(rawHeight, MIN_PANEL_HEIGHT), maxHeight);
      if (onExpandRef.current) {
        onExpandRef.current(clamped);
      }
      return;
    }

    const clamped = Math.min(Math.max(rawHeight, MIN_PANEL_HEIGHT), maxHeight);
    onResizeRef.current(clamped);
  }, []);

  // One controller drops both document listeners, so neither handler references the other
  const dragListeners = useRef<AbortController | null>(null);

  const endDrag = useCallback(() => {
    isDragging.current = false;
    isCollapsed.current = false;
    dragListeners.current?.abort();
    dragListeners.current = null;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    isCollapsed.current = false;
    startY.current = e.clientY;
    // Capture the current panel height from the panel's bounding rect
    const panel = (e.currentTarget as HTMLElement).closest('[data-testid="bottom-panel"]');
    startHeight.current = panel ? panel.getBoundingClientRect().height : 250;
    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
    dragListeners.current?.abort();
    const controller = new AbortController();
    dragListeners.current = controller;
    document.addEventListener('mousemove', handleMouseMove, { signal: controller.signal });
    document.addEventListener('mouseup', endDrag, { signal: controller.signal });
  }, [handleMouseMove, endDrag]);

  useEffect(() => {
    return () => {
      dragListeners.current?.abort();
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, []);

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
