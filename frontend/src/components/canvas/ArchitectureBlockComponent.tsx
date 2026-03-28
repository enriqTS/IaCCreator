'use client';

import { useRef, useCallback, useEffect } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { AWS_ICON_REGISTRY } from '@/data/aws-icon-registry';
import type { ArchitectureBlock } from '@/types/diagram';
import type { ServiceType } from '@/types/diagram';

function getIconPath(serviceType: ServiceType): string {
  for (const category of AWS_ICON_REGISTRY) {
    for (const service of category.services) {
      if (service.serviceType === serviceType) return service.iconPath;
    }
  }
  return '';
}

/** Padding in pixels on each side of the icon within the block */
export const ICON_PADDING = 12;

/** Determine whether a label should be shown for the given name */
export function shouldShowLabel(name: string): boolean {
  return name.trim() !== '' && name.trim() !== 'Service';
}

interface ArchitectureBlockComponentProps {
  block: ArchitectureBlock;
  isSelected: boolean;
}

export default function ArchitectureBlockComponent({ block, isSelected }: ArchitectureBlockComponentProps) {
  const selectObject = useDiagramStore((s) => s.selectObject);
  const toggleObjectSelection = useDiagramStore((s) => s.toggleObjectSelection);
  const moveSelectedObjects = useDiagramStore((s) => s.moveSelectedObjects);
  const iconPath = getIconPath(block.serviceType);

  const { width, height } = block.visualConfig;

  const showLabel = shouldShowLabel(block.name);
  const labelSpace = showLabel ? 20 : 0;
  const iconSize = Math.max(0, Math.min(width - 2 * ICON_PADDING, height - 2 * ICON_PADDING - labelSpace));

  const borderColor = isSelected
    ? 'rgba(59, 130, 246, 0.8)'
    : 'transparent';

  const isDragging = useRef(false);
  const didDrag = useRef(false);
  const lastMouse = useRef<{ x: number; y: number } | null>(null);
  const pendingSelectionId = useRef<string | null>(null);

  // Retry mechanism: if selectObject was dispatched but the store doesn't
  // reflect the selection after a tick, re-dispatch to ensure the BottomPanel opens.
  useEffect(() => {
    if (!pendingSelectionId.current) return;
    const expectedId = pendingSelectionId.current;
    pendingSelectionId.current = null;

    const raf = requestAnimationFrame(() => {
      const { selectedObjectIds } = useDiagramStore.getState();
      if (!selectedObjectIds.has(expectedId)) {
        // Selection didn't stick — retry once
        selectObject(expectedId);
      }
    });
    return () => cancelAnimationFrame(raf);
  });

  const dispatchSelect = useCallback(
    (id: string) => {
      selectObject(id);
      pendingSelectionId.current = id;
    },
    [selectObject],
  );

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;

    // In placement mode, let the DragSizingOverlay handle the mousedown instead
    const tool = useDiagramStore.getState().activeTool;
    if (typeof tool === 'object' && (tool.type === 'place-service' || tool.type === 'place-shape')) return;

    // Locked: allow selection but prevent drag
    if (block.locked) {
      e.stopPropagation();
      if (e.shiftKey) {
        toggleObjectSelection(block.id);
      } else {
        dispatchSelect(block.id);
      }
      return;
    }

    e.stopPropagation();
    useDiagramStore.getState().beginDragGesture();

    // If shift is not held and the object is not already selected, select it immediately
    // so that dragging works right away
    if (!e.shiftKey && !isSelected) {
      dispatchSelect(block.id);
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
        // It was a click, not a drag
        if (ev.shiftKey) {
          toggleObjectSelection(block.id);
        } else {
          dispatchSelect(block.id);
        }
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  }, [block.id, block.locked, isSelected, dispatchSelect, toggleObjectSelection, moveSelectedObjects]);

  return (
    <div
      data-testid={`architecture-block-${block.id}`}
      data-object-id={block.id}
      onMouseDown={handleMouseDown}
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        transform: `translate(${block.position.x - width / 2}px, ${block.position.y - height / 2}px)`,
        width: `${width}px`,
        height: `${height}px`,
        pointerEvents: 'auto',
        cursor: block.locked ? 'not-allowed' : 'grab',
        userSelect: 'none',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '4px',
        border: `2px solid ${borderColor}`,
        borderRadius: '4px',
        transition: 'border-color 0.15s',
        overflow: 'hidden',
      }}
    >
      {block.locked && (
        <span
          data-testid={`lock-badge-${block.id}`}
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
      {iconPath && (
        <img
          src={iconPath}
          alt={block.serviceType}
          width={iconSize}
          height={iconSize}
          draggable={false}
          style={{ pointerEvents: 'none', flexShrink: 0 }}
        />
      )}
      {showLabel && (
        <span
          style={{
            fontSize: '11px',
            color: 'rgba(255, 255, 255, 0.8)',
            whiteSpace: 'nowrap',
            maxWidth: `${width - 8}px`,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            textAlign: 'center',
          }}
        >
          {block.name}
        </span>
      )}
    </div>
  );
}
