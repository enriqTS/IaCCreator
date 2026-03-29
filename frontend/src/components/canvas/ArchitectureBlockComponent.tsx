'use client';

import { AWS_ICON_REGISTRY } from '@/data/aws-icon-registry';
import { useSnapDrag } from '@/hooks/useSnapDrag';
import AlignmentGuides from '@/components/canvas/AlignmentGuides';
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
export const ICON_PADDING = 0;

/** Determine whether a label should be shown for the given name */
export function shouldShowLabel(name: string): boolean {
  return name.trim() !== '' && name.trim() !== 'Service';
}

interface ArchitectureBlockComponentProps {
  block: ArchitectureBlock;
  isSelected: boolean;
}

export default function ArchitectureBlockComponent({ block, isSelected }: ArchitectureBlockComponentProps) {
  const iconPath = getIconPath(block.serviceType);

  const { width, height } = block.visualConfig;

  const showLabel = shouldShowLabel(block.name);
  const labelSpace = showLabel ? 20 : 0;
  const iconSize = Math.max(0, Math.min(width - 2 * ICON_PADDING, height - 2 * ICON_PADDING - labelSpace));

  const borderColor = isSelected
    ? 'rgba(59, 130, 246, 0.8)'
    : 'transparent';

  const { handleMouseDown, alignmentGuides } = useSnapDrag({
    objectId: block.id,
    isSelected,
    locked: block.locked,
  });

  return (
    <>
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
          boxSizing: 'border-box',
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
      {alignmentGuides.length > 0 && <AlignmentGuides guides={alignmentGuides} />}
    </>
  );
}
