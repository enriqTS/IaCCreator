'use client';

import { AWS_ICON_REGISTRY } from '@/data/aws-icon-registry';
import { useSnapDrag } from '@/hooks/useSnapDrag';
import AlignmentGuides from '@/components/canvas/AlignmentGuides';
import { GAP } from '@/hooks/useServiceNameLabels';
import { BUNDLED_SCHEMAS } from '@/data/bundled-schemas';
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

/**
 * Get the display name for a block from its terraform variables.
 * Uses the first variable in the schema (which is always the resource name field).
 * Returns the value if set and non-empty, otherwise null.
 */
export function getBlockDisplayName(block: ArchitectureBlock): string | null {
  const schema = BUNDLED_SCHEMAS[block.serviceType];
  if (!schema || schema.length === 0) return null;

  const nameField = schema[0].name;
  const value = block.terraformVariables[nameField];

  if (value === undefined || value === null || value === '') return null;
  return String(value).trim() || null;
}

interface ArchitectureBlockComponentProps {
  block: ArchitectureBlock;
  isSelected: boolean;
}

export default function ArchitectureBlockComponent({ block, isSelected }: ArchitectureBlockComponentProps) {
  const iconPath = getIconPath(block.serviceType);

  const { width, height } = block.visualConfig;

  const displayName = getBlockDisplayName(block);

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
            height={height}
            draggable={false}
            style={{ pointerEvents: 'none', display: 'block', objectFit: 'contain' }}
          />
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
      {/* Service name label rendered as sibling below the block */}
      {displayName && (
        <span
          data-testid={`service-label-${block.id}`}
          style={{
            position: 'absolute',
            left: block.position.x - width / 2,
            top: block.position.y + height / 2 + GAP,
            width: `${width}px`,
            fontSize: '11px',
            color: 'rgba(255, 255, 255, 0.9)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            textAlign: 'center',
            pointerEvents: 'none',
          }}
        >
          {displayName}
        </span>
      )}
      {alignmentGuides.length > 0 && <AlignmentGuides guides={alignmentGuides} />}
    </>
  );
}
