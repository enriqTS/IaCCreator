'use client';

import { useEffect, useState } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { screenToCanvas, canvasToScreen } from '@/utils/viewport';
import { AWS_ICON_REGISTRY } from '@/data/aws-icon-registry';
import { DEFAULT_BLOCK_VISUAL } from '@/types/diagram';
import type { ServiceType, Point } from '@/types/diagram';

function getIconPath(serviceType: ServiceType): string {
  for (const category of AWS_ICON_REGISTRY) {
    for (const service of category.services) {
      if (service.serviceType === serviceType) return service.iconPath;
    }
  }
  return '';
}

interface PlacementPreviewProps {
  containerRef: React.RefObject<HTMLDivElement | null>;
}

export default function PlacementPreview({ containerRef }: PlacementPreviewProps) {
  const activeTool = useDiagramStore((s) => s.activeTool);
  const viewport = useDiagramStore((s) => s.viewport);
  const setActiveTool = useDiagramStore((s) => s.setActiveTool);

  // Ephemeral local state: mouse position in screen coords relative to container
  const [mouseScreen, setMouseScreen] = useState<Point | null>(null);

  const isPlaceService = typeof activeTool === 'object' && activeTool.type === 'place-service';
  const isActive = isPlaceService;

  // Track mouse position over the canvas container
  useEffect(() => {
    if (!isActive) {
      setMouseScreen(null);
      return;
    }

    const container = containerRef.current;
    if (!container) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      setMouseScreen({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    };

    const handleMouseLeave = () => {
      setMouseScreen(null);
    };

    container.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('mouseleave', handleMouseLeave);
    return () => {
      container.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [isActive, containerRef]);

  // Cancel placement on Escape key
  useEffect(() => {
    if (!isActive) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setActiveTool('pointer');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isActive, setActiveTool]);

  if (!isActive || !mouseScreen) return null;

  // Convert screen mouse position to canvas coordinates, then back to screen
  // to get the snapped screen position that accounts for viewport transform
  const canvasPos = screenToCanvas(mouseScreen, viewport);
  const screenPos = canvasToScreen(canvasPos, viewport);

  if (isPlaceService) {
    const serviceType = (activeTool as { type: 'place-service'; serviceType: ServiceType }).serviceType;
    const iconPath = getIconPath(serviceType);
    const { width, height } = DEFAULT_BLOCK_VISUAL;
    const scaledWidth = width * viewport.scale;
    const scaledHeight = height * viewport.scale;

    return (
      <div
        data-testid="placement-preview"
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          transform: `translate(${screenPos.x - scaledWidth / 2}px, ${screenPos.y - scaledHeight / 2}px)`,
          width: `${scaledWidth}px`,
          height: `${scaledHeight}px`,
          opacity: 0.5,
          pointerEvents: 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '4px',
          borderRadius: '8px',
          border: '2px solid rgba(59, 130, 246, 0.6)',
          backgroundColor: 'rgba(30, 30, 30, 0.9)',
          overflow: 'hidden',
        }}
      >
        {iconPath && (
          <img
            src={iconPath}
            alt={serviceType}
            width={Math.min(40, scaledWidth * 0.5)}
            height={Math.min(40, scaledHeight * 0.5)}
            draggable={false}
            style={{ pointerEvents: 'none', flexShrink: 0 }}
          />
        )}
        <span
          style={{
            fontSize: '11px',
            color: 'rgba(255, 255, 255, 0.8)',
            whiteSpace: 'nowrap',
            textAlign: 'center',
          }}
        >
          {serviceType}
        </span>
      </div>
    );
  }

  return null;
}
