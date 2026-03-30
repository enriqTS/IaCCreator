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
          boxSizing: 'border-box',
          overflow: 'hidden',
        }}
      >
        {/* Icon fills the entire block */}
        {iconPath && (
          <img
            src={iconPath}
            alt={block.serviceType}
            width={width}
            height={showLabel ? height - 18 : height}
            draggable={false}
            style={{ pointerEvents: 'none', display: 'block', objectFit: 'contain' }}
          />
        )}
        {/* Label at the bottom, overlaid on the icon */}
        {showLabel && (
          <span
            style={{
              position: 'absolute',
              bottom: 2,
              left: 0,
              right: 0,
              fontSize: '11px',
              color: 'rgba(255, 255, 255, 0.9)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              textAlign: 'center',
              textShadow: '0 1px 3px rgba(0,0,0,0.7)',
              pointerEvents: 'none',
            }}
          >
            {block.name}
          </span>
        )}
        {/* Selection border drawn on top of the image */}
        {isSelected && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              border: '2px solid rgba(59, 130, 246, 0.8)',
              borderRadius: '4px',
              pointerEvents: 'none',
            }}
          />
        )}
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
      </div>
      {alignmentGuides.length > 0 && <AlignmentGuides guides={alignmentGuides} />}
    </>
  );
}
