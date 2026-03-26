'use client';

import { useDiagramStore } from '@/store/diagram-store';
import { canvasToScreen } from '@/utils/viewport';
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

interface ArchitectureBlockComponentProps {
  block: ArchitectureBlock;
  isSelected: boolean;
}

export default function ArchitectureBlockComponent({ block, isSelected }: ArchitectureBlockComponentProps) {
  const viewport = useDiagramStore((s) => s.viewport);
  const selectObject = useDiagramStore((s) => s.selectObject);
  const iconPath = getIconPath(block.serviceType);

  const { width, height } = block.visualConfig;
  const screenPos = canvasToScreen(block.position, viewport);

  const scaledWidth = width * viewport.scale;
  const scaledHeight = height * viewport.scale;

  const borderColor = isSelected
    ? 'rgba(59, 130, 246, 0.8)'
    : 'rgba(255, 255, 255, 0.1)';

  return (
    <div
      data-testid={`architecture-block-${block.id}`}
      onClick={(e) => {
        e.stopPropagation();
        selectObject(block.id);
      }}
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        transform: `translate(${screenPos.x - scaledWidth / 2}px, ${screenPos.y - scaledHeight / 2}px)`,
        width: `${scaledWidth}px`,
        height: `${scaledHeight}px`,
        pointerEvents: 'auto',
        cursor: 'grab',
        userSelect: 'none',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '4px',
        borderRadius: '8px',
        border: `2px solid ${borderColor}`,
        backgroundColor: 'rgba(30, 30, 30, 0.9)',
        transition: 'border-color 0.15s',
        overflow: 'hidden',
      }}
    >
      {iconPath && (
        <img
          src={iconPath}
          alt={block.serviceType}
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
          maxWidth: `${scaledWidth - 8}px`,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          textAlign: 'center',
        }}
      >
        {block.name}
      </span>
    </div>
  );
}
