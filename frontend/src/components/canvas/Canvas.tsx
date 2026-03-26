'use client';

import { useRef, useEffect, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { screenToCanvas } from '@/utils/viewport';
import CanvasBackground from './CanvasBackground';
import ElementLayer from './ElementLayer';

export default function Canvas() {
  const containerRef = useRef<HTMLDivElement>(null);

  // Pan state refs
  const isPanning = useRef(false);
  const panStart = useRef<{ x: number; y: number } | null>(null);
  const isSpaceHeld = useRef(false);

  // Store actions (stable references)
  const zoom = useDiagramStore((s) => s.zoom);
  const pan = useDiagramStore((s) => s.pan);
  const selectElement = useDiagramStore((s) => s.selectElement);
  const selectConnector = useDiagramStore((s) => s.selectConnector);
  const addElement = useDiagramStore((s) => s.addElement);
  const setActiveTool = useDiagramStore((s) => s.setActiveTool);
  const activeTool = useDiagramStore((s) => s.activeTool);
  const viewport = useDiagramStore((s) => s.viewport);

  // --- Wheel → Zoom ---
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 0.9 : 1.1;
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const cursorScreen = { x: e.clientX - rect.left, y: e.clientY - rect.top };
      zoom(factor, cursorScreen);
    },
    [zoom],
  );

  // --- Middle-click drag → Pan ---
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      // Middle-click (button 1) starts pan
      if (e.button === 1) {
        e.preventDefault();
        isPanning.current = true;
        panStart.current = { x: e.clientX, y: e.clientY };
        return;
      }

      // Space + left-click starts pan
      if (e.button === 0 && isSpaceHeld.current) {
        e.preventDefault();
        isPanning.current = true;
        panStart.current = { x: e.clientX, y: e.clientY };
        return;
      }

      // Left-click on empty canvas
      if (e.button === 0 && e.target === e.currentTarget) {
        // Place-service mode: add element at click position
        if (typeof activeTool === 'object' && activeTool.type === 'place-service') {
          const rect = containerRef.current?.getBoundingClientRect();
          if (!rect) return;
          const screenPoint = { x: e.clientX - rect.left, y: e.clientY - rect.top };
          const canvasPoint = screenToCanvas(screenPoint, viewport);
          addElement(activeTool.serviceType, canvasPoint);
          setActiveTool('pointer');
          return;
        }

        // Deselect everything and cancel pending connector
        selectElement(null);
        selectConnector(null);
        useDiagramStore.setState({ pendingConnectorSourceId: null });
      }
    },
    [activeTool, viewport, addElement, setActiveTool, selectElement, selectConnector],
  );

  // Global mousemove/mouseup for pan (attached on mount)
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isPanning.current || !panStart.current) return;
      const dx = e.clientX - panStart.current.x;
      const dy = e.clientY - panStart.current.y;
      panStart.current = { x: e.clientX, y: e.clientY };
      pan(dx, dy);
    };

    const handleMouseUp = (e: MouseEvent) => {
      if (e.button === 1 || (e.button === 0 && isSpaceHeld.current)) {
        isPanning.current = false;
        panStart.current = null;
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [pan]);

  // Space key tracking for space+drag pan
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !e.repeat) {
        // Prevent page scroll when space is pressed
        if (e.target === document.body || containerRef.current?.contains(e.target as Node)) {
          e.preventDefault();
        }
        isSpaceHeld.current = true;
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        isSpaceHeld.current = false;
        // End any active pan when space is released
        if (isPanning.current) {
          isPanning.current = false;
          panStart.current = null;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  // Prevent default middle-click auto-scroll behavior
  const handleAuxClick = useCallback((e: React.MouseEvent) => {
    if (e.button === 1) e.preventDefault();
  }, []);

  // Determine cursor based on state
  let cursor = 'default';
  if (isSpaceHeld.current || isPanning.current) {
    cursor = 'grab';
  } else if (typeof activeTool === 'object' && activeTool.type === 'place-service') {
    cursor = 'crosshair';
  }

  return (
    <div
      ref={containerRef}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onAuxClick={handleAuxClick}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        cursor,
      }}
    >
      <CanvasBackground />
      <ElementLayer />
    </div>
  );
}
