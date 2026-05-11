'use client';

import { useRef, useState, useEffect, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { screenToCanvas, canvasToScreen } from '@/utils/viewport';
import { DEFAULT_LINE_VISUAL, DEFAULT_GEO_VISUAL, DEFAULT_BLOCK_VISUAL, DEFAULT_TEXT_VISUAL, DEFAULT_UML_VISUAL, DEFAULT_UML_CLASS_DATA } from '@/types/diagram';
import type { Point } from '@/types/diagram';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { snapPointToGrid } from '@/utils/snap';
import CanvasBackground from './CanvasBackground';
import ElementLayer from './ElementLayer';
import PlacementPreview from './PlacementPreview';
import DragSizingOverlay from './DragSizingOverlay';
import MarqueeSelection from './MarqueeSelection';
import CanvasObjectContextMenu from './CanvasObjectContextMenu';
import CanvasContextMenu from './CanvasContextMenu';
import InlineRenameOverlay from './InlineRenameOverlay';
import PullToConnectOverlay from './PullToConnectOverlay';

type ContextMenuState =
  | { type: 'object'; objectId: string; x: number; y: number }
  | { type: 'canvas'; x: number; y: number; canvasPosition: { x: number; y: number } };

export default function Canvas() {
  const containerRef = useRef<HTMLDivElement>(null);

  // Pan state refs
  const isPanning = useRef(false);
  const panStart = useRef<{ x: number; y: number } | null>(null);
  const isSpaceHeld = useRef(false);

  // Line placement state
  const [lineStart, setLineStart] = useState<Point | null>(null);
  const [linePreviewEnd, setLinePreviewEnd] = useState<Point | null>(null);

  // Context menu state
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);

  // Inline rename overlay state
  const [renamingObjectId, setRenamingObjectId] = useState<string | null>(null);

  // Store actions (stable references)
  const zoom = useDiagramStore((s) => s.zoom);
  const pan = useDiagramStore((s) => s.pan);
  const selectElement = useDiagramStore((s) => s.selectElement);
  const selectConnector = useDiagramStore((s) => s.selectConnector);
  const addCanvasObject = useDiagramStore((s) => s.addCanvasObject);
  const removeCanvasObject = useDiagramStore((s) => s.removeCanvasObject);
  const selectedObjectIds = useDiagramStore((s) => s.selectedObjectIds);
  const clearSelection = useDiagramStore((s) => s.clearSelection);
  const setActiveTool = useDiagramStore((s) => s.setActiveTool);
  const activeTool = useDiagramStore((s) => s.activeTool);
  const viewport = useDiagramStore((s) => s.viewport);
  const setEditingTextId = useDiagramStore((s) => s.setEditingTextId);

  // Reset line placement state when tool changes away from 'line'
  useEffect(() => {
    if (activeTool !== 'line') {
      setLineStart(null);
      setLinePreviewEnd(null);
    }
  }, [activeTool]);

  // --- handlePlaceObject: called by DragSizingOverlay on mouseup ---
  const handlePlaceObject = useCallback(
    (payload: { canvasPosition: Point; width: number; height: number }) => {
      const tool = useDiagramStore.getState().activeTool;

      if (typeof tool === 'object' && tool.type === 'place-service') {
        // width/height === 0 means simple click → use default dimensions
        if (payload.width > 0 && payload.height > 0) {
          addCanvasObject({
            objectType: 'architecture-block',
            serviceType: tool.serviceType,
            name: 'Service',
            position: payload.canvasPosition,
            config: {},
            terraformVariables: {},
            visualConfig: { width: payload.width, height: payload.height },
          });
        } else {
          addCanvasObject({
            objectType: 'architecture-block',
            serviceType: tool.serviceType,
            name: 'Service',
            position: payload.canvasPosition,
            config: {},
            terraformVariables: {},
            visualConfig: { ...DEFAULT_BLOCK_VISUAL },
          });
        }
        setActiveTool('pointer');
        return;
      }

      if (typeof tool === 'object' && tool.type === 'place-shape') {
        if (payload.width > 0 && payload.height > 0) {
          addCanvasObject({
            objectType: 'geometric',
            name: 'Shape',
            position: payload.canvasPosition,
            visualConfig: { ...DEFAULT_GEO_VISUAL, shape: tool.shape, width: payload.width, height: payload.height },
          });
        } else {
          addCanvasObject({
            objectType: 'geometric',
            name: 'Shape',
            position: payload.canvasPosition,
            visualConfig: { ...DEFAULT_GEO_VISUAL, shape: tool.shape },
          });
        }
        setActiveTool('pointer');
        return;
      }

      if (typeof tool === 'object' && tool.type === 'place-uml') {
        const umlPayload: Parameters<typeof addCanvasObject>[0] = {
          objectType: 'uml',
          name: tool.umlKind.charAt(0).toUpperCase() + tool.umlKind.slice(1),
          position: payload.canvasPosition,
          umlKind: tool.umlKind,
          visualConfig: { ...DEFAULT_UML_VISUAL },
        };
        if (tool.umlKind === 'class' || tool.umlKind === 'interface') {
          (umlPayload as Record<string, unknown>).classData = { ...DEFAULT_UML_CLASS_DATA };
        }
        if (payload.width > 0 && payload.height > 0) {
          (umlPayload.visualConfig as unknown as Record<string, unknown>).width = payload.width;
          (umlPayload.visualConfig as unknown as Record<string, unknown>).height = payload.height;
        }
        addCanvasObject(umlPayload);
        setActiveTool('pointer');
        return;
      }
    },
    [addCanvasObject, setActiveTool],
  );

  // --- Wheel → Zoom (non-passive to allow preventDefault) ---
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 0.9 : 1.1;
      const rect = container.getBoundingClientRect();
      const cursorScreen = { x: e.clientX - rect.left, y: e.clientY - rect.top };
      zoom(factor, cursorScreen);
    };

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
  }, [zoom]);

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

      // Left-click on empty canvas (target is either the container itself or the background canvas)
      const target = e.target as HTMLElement;
      const isCanvasBackground = target === e.currentTarget || target.tagName === 'CANVAS';
      if (e.button === 0 && isCanvasBackground) {
        // Line tool mode: first click records start, second click creates line
        if (activeTool === 'line') {
          const rect = containerRef.current?.getBoundingClientRect();
          if (!rect) return;
          const screenPoint = { x: e.clientX - rect.left, y: e.clientY - rect.top };
          const canvasPoint = screenToCanvas(screenPoint, viewport);

          // Snap line click position to grid when snap is enabled and Alt is not held
          const { snapToGridEnabled, gridCellSize } = useLayoutPreferencesStore.getState();
          const snappedCanvasPoint = (snapToGridEnabled && !e.altKey)
            ? snapPointToGrid(canvasPoint, gridCellSize)
            : canvasPoint;

          if (!lineStart) {
            // First click: record start point
            setLineStart(snappedCanvasPoint);
            setLinePreviewEnd(snappedCanvasPoint);
          } else {
            // Second click: create the line object
            addCanvasObject({
              objectType: 'line',
              name: 'Line',
              start: lineStart,
              end: snappedCanvasPoint,
              sourceAnchor: null,
              targetAnchor: null,
              visualConfig: { ...DEFAULT_LINE_VISUAL },
            });
            setLineStart(null);
            setLinePreviewEnd(null);
          }
          return;
        }

        // Place-service and place-shape modes are now handled by DragSizingOverlay
        if (typeof activeTool === 'object' && (activeTool.type === 'place-service' || activeTool.type === 'place-shape' || activeTool.type === 'place-uml')) {
          return;
        }

        // Deselect everything and cancel pending connector
        selectElement(null);
        selectConnector(null);
        clearSelection();
        useDiagramStore.setState({ pendingConnectorSourceId: null });
      }
    },
    [activeTool, viewport, lineStart, addCanvasObject, selectElement, selectConnector, clearSelection],
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
        // Allow spacebar in text inputs (textarea, input, contenteditable)
        const target = e.target as HTMLElement;
        if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT' || target.isContentEditable) {
          return;
        }
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
  // Note: The primary handler is in page.tsx; this is a fallback for when
  // Canvas is rendered outside the page context (e.g., tests).
  useEffect(() => {
    const handleDeleteKey = (e: KeyboardEvent) => {
      if (e.key !== 'Delete' && e.key !== 'Backspace') return;

      const target = e.target as HTMLElement;
      const isTyping =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable;

      // If typing inside an inline canvas editor, let it behave normally
      if (isTyping && target.closest('[data-testid="viewport-transform-container"]')) return;

      // If typing inside the sidebar, blur and delete the selected objects
      if (isTyping && target.closest('[data-testid="sidebar-panel"]')) {
        const currentSelectedIds = useDiagramStore.getState().selectedObjectIds;
        if (currentSelectedIds.size > 0) {
          e.preventDefault();
          (document.activeElement as HTMLElement)?.blur();
          for (const id of currentSelectedIds) {
            useDiagramStore.getState().removeCanvasObject(id);
          }
        }
        return;
      }

      // If typing in some other input (e.g. dialog), let it behave normally
      if (isTyping) return;

      const currentSelectedIds = useDiagramStore.getState().selectedObjectIds;
      if (currentSelectedIds.size > 0) {
        e.preventDefault();
        for (const id of currentSelectedIds) {
          useDiagramStore.getState().removeCanvasObject(id);
        }
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

  // Double-click handler for text creation (Task 11.1)
  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      // Only handle double-click with pointer tool
      const tool = useDiagramStore.getState().activeTool;
      if (tool !== 'pointer') return;

      // Check if double-click is on empty canvas (not on an existing object)
      // Walk up from target to see if we hit a canvas object
      let target = e.target as HTMLElement | null;
      while (target && target !== e.currentTarget) {
        if (target.getAttribute('data-object-id')) {
          // Double-click on existing object — TextObjectComponent handles its own double-click for editing
          return;
        }
        target = target.parentElement;
      }

      // Double-click on empty canvas: create a text object and enter editing mode
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const screenPoint = { x: e.clientX - rect.left, y: e.clientY - rect.top };
      const vp = useDiagramStore.getState().viewport;
      const canvasPoint = screenToCanvas(screenPoint, vp);

      // Snap text creation position to grid when snap is enabled
      const { snapToGridEnabled: snapEnabled, gridCellSize: cellSize } = useLayoutPreferencesStore.getState();
      const snappedTextPoint = snapEnabled
        ? snapPointToGrid(canvasPoint, cellSize)
        : canvasPoint;

      const store = useDiagramStore.getState();
      store.addCanvasObject({
        objectType: 'text',
        name: 'Text',
        position: snappedTextPoint,
        content: 'Text',
        visualConfig: { ...DEFAULT_TEXT_VISUAL },
      });

      // Find the newly created text object (it will be the last one added)
      const updatedObjects = useDiagramStore.getState().canvasObjects;
      let newTextId: string | null = null;
      for (const [id, obj] of updatedObjects) {
        if (obj.objectType === 'text' && obj.position.x === snappedTextPoint.x && obj.position.y === snappedTextPoint.y) {
          newTextId = id;
        }
      }
      if (newTextId) {
        useDiagramStore.getState().setEditingTextId(newTextId);
      }
    },
    [],
  );

  // Right-click context menu for canvas objects
  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      // Walk up from the target to find a canvas object element with data-object-id
      let target = e.target as HTMLElement | null;
      while (target && target !== e.currentTarget) {
        const objectId = target.getAttribute('data-object-id');
        if (objectId) {
          e.preventDefault();
          // Select the object if not already selected
          const store = useDiagramStore.getState();
          if (!store.selectedObjectIds.has(objectId)) {
            store.selectObject(objectId);
          }
          setContextMenu({ type: 'object', objectId, x: e.clientX, y: e.clientY });
          return;
        }
        target = target.parentElement;
      }
      // Right-click on empty canvas — open canvas context menu
      e.preventDefault();
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const screenPoint = { x: e.clientX - rect.left, y: e.clientY - rect.top };
      const vp = useDiagramStore.getState().viewport;
      const canvasPosition = screenToCanvas(screenPoint, vp);
      setContextMenu({ type: 'canvas', x: e.clientX, y: e.clientY, canvasPosition });
    },
    [],
  );

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
  } else if (typeof activeTool === 'object' && activeTool.type === 'place-uml') {
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
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onAuxClick={handleAuxClick}
      onContextMenu={handleContextMenu}
      onDoubleClick={handleDoubleClick}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        cursor,
      }}
    >
      <CanvasBackground />
      {/* Viewport transform container: positions ElementLayer children in canvas coordinates */}
      <div
        data-testid="viewport-transform-container"
        style={{
          position: 'absolute',
          inset: 0,
          transformOrigin: '0 0',
          transform: `translate(${viewport.offsetX}px, ${viewport.offsetY}px) scale(${viewport.scale})`,
          pointerEvents: 'none',
        }}
      >
        <ElementLayer />
        <PullToConnectOverlay />
      </div>

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

      {/* Placement preview ghost that follows mouse during place-service / place-shape */}
      <PlacementPreview containerRef={containerRef} />

      {/* Drag-sizing overlay for click-and-drag placement */}
      <DragSizingOverlay containerRef={containerRef} onPlaceObject={handlePlaceObject} />

      {/* Marquee multi-selection rectangle */}
      <MarqueeSelection containerRef={containerRef} />

      {/* Right-click context menu */}
      {contextMenu?.type === 'object' && (
        <CanvasObjectContextMenu
          menu={{ objectId: contextMenu.objectId, x: contextMenu.x, y: contextMenu.y }}
          onClose={() => setContextMenu(null)}
          onRename={(id) => { setContextMenu(null); setRenamingObjectId(id); }}
        />
      )}
      {contextMenu?.type === 'canvas' && (
        <CanvasContextMenu
          menu={{ x: contextMenu.x, y: contextMenu.y, canvasPosition: contextMenu.canvasPosition }}
          onClose={() => setContextMenu(null)}
        />
      )}

      {/* Inline rename overlay */}
      {renamingObjectId && (
        <InlineRenameOverlay
          objectId={renamingObjectId}
          onClose={() => setRenamingObjectId(null)}
        />
      )}
    </div>
  );
}
