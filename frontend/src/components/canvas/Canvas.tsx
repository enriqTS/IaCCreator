'use client';

import { useRef, useState, useEffect, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { screenToCanvas, canvasToScreen } from '@/utils/viewport';
import { DEFAULT_LINE_VISUAL, DEFAULT_GEO_VISUAL } from '@/types/diagram';
import type { Point } from '@/types/diagram';
import CanvasBackground from './CanvasBackground';
import ElementLayer from './ElementLayer';

export default function Canvas() {
  const containerRef = useRef<HTMLDivElement>(null);

  // Pan state refs
  const isPanning = useRef(false);
  const panStart = useRef<{ x: number; y: number } | null>(null);
  const isSpaceHeld = useRef(false);

  // Line placement state
  const [lineStart, setLineStart] = useState<Point | null>(null);
  const [linePreviewEnd, setLinePreviewEnd] = useState<Point | null>(null);

  // Store actions (stable references)
  const zoom = useDiagramStore((s) => s.zoom);
  const pan = useDiagramStore((s) => s.pan);
  const selectElement = useDiagramStore((s) => s.selectElement);
  const selectConnector = useDiagramStore((s) => s.selectConnector);
  const addElement = useDiagramStore((s) => s.addElement);
  const addCanvasObject = useDiagramStore((s) => s.addCanvasObject);
  const selectObject = useDiagramStore((s) => s.selectObject);
  const removeCanvasObject = useDiagramStore((s) => s.removeCanvasObject);
  const selectedObjectId = useDiagramStore((s) => s.selectedObjectId);
  const setActiveTool = useDiagramStore((s) => s.setActiveTool);
  const activeTool = useDiagramStore((s) => s.activeTool);
  const viewport = useDiagramStore((s) => s.viewport);

  // Reset line placement state when tool changes away from 'line'
  useEffect(() => {
    if (activeTool !== 'line') {
      setLineStart(null);
      setLinePreviewEnd(null);
    }
  }, [activeTool]);

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
        // Line tool mode: first click records start, second click creates line
        if (activeTool === 'line') {
          const rect = containerRef.current?.getBoundingClientRect();
          if (!rect) return;
          const screenPoint = { x: e.clientX - rect.left, y: e.clientY - rect.top };
          const canvasPoint = screenToCanvas(screenPoint, viewport);

          if (!lineStart) {
            // First click: record start point
            setLineStart(canvasPoint);
            setLinePreviewEnd(canvasPoint);
          } else {
            // Second click: create the line object
            addCanvasObject({
              objectType: 'line',
              name: 'Line',
              start: lineStart,
              end: canvasPoint,
              visualConfig: { ...DEFAULT_LINE_VISUAL },
            });
            setLineStart(null);
            setLinePreviewEnd(null);
          }
          return;
        }

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

        // Place-shape mode: create geometric object at click position
        if (typeof activeTool === 'object' && activeTool.type === 'place-shape') {
          const rect = containerRef.current?.getBoundingClientRect();
          if (!rect) return;
          const screenPoint = { x: e.clientX - rect.left, y: e.clientY - rect.top };
          const canvasPoint = screenToCanvas(screenPoint, viewport);
          addCanvasObject({
            objectType: 'geometric',
            name: 'Shape',
            position: canvasPoint,
            visualConfig: { ...DEFAULT_GEO_VISUAL, shape: activeTool.shape },
          });
          setActiveTool('pointer');
          return;
        }

        // Deselect everything and cancel pending connector
        selectElement(null);
        selectConnector(null);
        selectObject(null);
        useDiagramStore.setState({ pendingConnectorSourceId: null });
      }
    },
    [activeTool, viewport, lineStart, addElement, addCanvasObject, setActiveTool, selectElement, selectConnector, selectObject],
  );

  // Mouse move handler for line preview and pan
  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      // Update line preview end position when in line mode with a start point
      if (activeTool === 'line' && lineStart) {
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;
        const screenPoint = { x: e.clientX - rect.left, y: e.clientY - rect.top };
        const canvasPoint = screenToCanvas(screenPoint, viewport);
        setLinePreviewEnd(canvasPoint);
      }
    },
    [activeTool, lineStart, viewport],
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

  // Delete/Backspace key handler for removing selected objects
  useEffect(() => {
    const handleDeleteKey = (e: KeyboardEvent) => {
      if (e.key !== 'Delete' && e.key !== 'Backspace') return;

      // Don't delete when user is typing in an input/textarea/contenteditable
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable
      ) {
        return;
      }

      const currentSelectedId = useDiagramStore.getState().selectedObjectId;
      if (currentSelectedId) {
        e.preventDefault();
        useDiagramStore.getState().removeCanvasObject(currentSelectedId);
      }
    };

    window.addEventListener('keydown', handleDeleteKey);
    return () => {
      window.removeEventListener('keydown', handleDeleteKey);
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
  } else if (activeTool === 'line') {
    cursor = 'crosshair';
  } else if (typeof activeTool === 'object' && activeTool.type === 'place-service') {
    cursor = 'crosshair';
  } else if (typeof activeTool === 'object' && activeTool.type === 'place-shape') {
    cursor = 'crosshair';
  }

  // Compute preview line screen coordinates
  const previewLineScreen =
    lineStart && linePreviewEnd
      ? {
          start: canvasToScreen(lineStart, viewport),
          end: canvasToScreen(linePreviewEnd, viewport),
        }
      : null;

  return (
    <div
      ref={containerRef}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
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

      {/* Preview line while placing a line object */}
      {previewLineScreen && (
        <svg
          data-testid="line-preview-svg"
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            overflow: 'visible',
          }}
        >
          <line
            x1={previewLineScreen.start.x}
            y1={previewLineScreen.start.y}
            x2={previewLineScreen.end.x}
            y2={previewLineScreen.end.y}
            stroke="#ffffff"
            strokeWidth={2}
            strokeDasharray="6 4"
            opacity={0.7}
          />
        </svg>
      )}
    </div>
  );
}
