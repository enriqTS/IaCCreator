'use client';

import { useRef, useCallback, useState } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasToScreen, screenToCanvas } from '@/utils/viewport';
import { AWS_ICON_REGISTRY } from '@/data/aws-icon-registry';
import type { DiagramElement } from '@/types/diagram';
import type { ServiceType } from '@/types/diagram';

function getIconPath(serviceType: ServiceType): string {
  for (const category of AWS_ICON_REGISTRY) {
    for (const service of category.services) {
      if (service.serviceType === serviceType) return service.iconPath;
    }
  }
  return '';
}

interface DiagramElementProps {
  element: DiagramElement;
}

export default function DiagramElementComponent({ element }: DiagramElementProps) {
  const viewport = useDiagramStore((s) => s.viewport);
  const selectedElementId = useDiagramStore((s) => s.selectedElementId);
  const activeTool = useDiagramStore((s) => s.activeTool);
  const selectElement = useDiagramStore((s) => s.selectElement);
  const updateElementPosition = useDiagramStore((s) => s.updateElementPosition);
  const pendingConnectorSourceId = useDiagramStore((s) => s.pendingConnectorSourceId);
  const addConnector = useDiagramStore((s) => s.addConnector);
  const setActiveTool = useDiagramStore((s) => s.setActiveTool);

  const [isHovered, setIsHovered] = useState(false);
  const isDragging = useRef(false);
  const dragStart = useRef<{ screenX: number; screenY: number; canvasX: number; canvasY: number } | null>(null);

  const isSelected = selectedElementId === element.id;
  const isConnectorMode = activeTool === 'connector';
  const iconPath = getIconPath(element.serviceType);

  const screenPos = canvasToScreen(element.position, viewport);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();

      if (isConnectorMode) {
        // In connector mode, handle source/target selection
        if (!pendingConnectorSourceId) {
          // Set this element as the connector source
          useDiagramStore.setState({ pendingConnectorSourceId: element.id });
        } else if (pendingConnectorSourceId !== element.id) {
          // Create connector from pending source to this element
          try {
            addConnector(pendingConnectorSourceId, element.id);
          } catch {
            // Ignore errors (e.g., self-connection — shouldn't happen here)
          }
          useDiagramStore.setState({ pendingConnectorSourceId: null });
        }
        return;
      }

      // Select the element
      selectElement(element.id);

      // Start drag tracking
      isDragging.current = false;
      dragStart.current = {
        screenX: e.clientX,
        screenY: e.clientY,
        canvasX: element.position.x,
        canvasY: element.position.y,
      };

      const handleMouseMove = (moveEvent: MouseEvent) => {
        if (!dragStart.current) return;
        isDragging.current = true;

        const dx = moveEvent.clientX - dragStart.current.screenX;
        const dy = moveEvent.clientY - dragStart.current.screenY;

        // Convert screen delta to canvas delta
        const newCanvasX = dragStart.current.canvasX + dx / viewport.scale;
        const newCanvasY = dragStart.current.canvasY + dy / viewport.scale;

        updateElementPosition(element.id, { x: newCanvasX, y: newCanvasY });
      };

      const handleMouseUp = () => {
        isDragging.current = false;
        dragStart.current = null;
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };

      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    },
    [isConnectorMode, pendingConnectorSourceId, element.id, element.position, selectElement, addConnector, updateElementPosition, viewport.scale],
  );

  // Build border style based on state
  let borderColor = 'rgba(255, 255, 255, 0.1)';
  if (isSelected) {
    borderColor = 'rgba(59, 130, 246, 0.8)'; // blue
  } else if (isHovered) {
    borderColor = 'rgba(255, 255, 255, 0.3)';
  }

  let backgroundColor = 'rgba(30, 30, 30, 0.9)';
  if (isHovered && !isSelected) {
    backgroundColor = 'rgba(40, 40, 40, 0.95)';
  }

  return (
    <div
      onMouseDown={handleMouseDown}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        transform: `translate(${screenPos.x - 32}px, ${screenPos.y - 32}px)`,
        pointerEvents: 'auto',
        cursor: isConnectorMode ? 'crosshair' : 'grab',
        userSelect: 'none',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '4px',
        padding: '8px',
        borderRadius: '8px',
        border: `2px solid ${borderColor}`,
        backgroundColor,
        transition: 'border-color 0.15s, background-color 0.15s',
        minWidth: '64px',
      }}
    >
      {iconPath && (
        <img
          src={iconPath}
          alt={element.serviceType}
          width={40}
          height={40}
          draggable={false}
          style={{ pointerEvents: 'none' }}
        />
      )}
      <span
        style={{
          fontSize: '11px',
          color: 'rgba(255, 255, 255, 0.8)',
          whiteSpace: 'nowrap',
          maxWidth: '80px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          textAlign: 'center',
        }}
      >
        {element.name}
      </span>
    </div>
  );
}
