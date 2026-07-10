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
 * Truncate a label to the specified max length, adding ellipsis if it exceeds the limit.
 */
export function truncateLabel(label: string, maxLength: number = 40): string {
  if (label.length > maxLength) {
    return label.slice(0, maxLength) + '...';
  }
  return label;
}

/**
 * Get the display name for a block.
 * Priority: custom name (block.name if non-empty) → block.defaultName (revert behavior).
 * Config-driven name (first schema variable) takes highest priority if set.
 * Truncates the displayed label at 40 characters with ellipsis.
 * Returns null only if no name source provides a non-empty string.
 */
export function getBlockDisplayName(block: ArchitectureBlock): string | null {
  // Highest priority: config-driven name (first schema variable)
  const schema = BUNDLED_SCHEMAS[block.serviceType];
  if (schema && schema.length > 0) {
    const nameField = schema[0].name;
    const value = (block.config as Record<string, unknown>)[nameField];

    if (value !== undefined && value !== null && value !== '') {
      const trimmed = String(value).trim();
      if (trimmed) return truncateLabel(trimmed);
    }
  }

  // Custom name set via config panel (block.name)
  if (block.name && block.name.trim()) {
    return truncateLabel(block.name.trim());
  }

  // Revert to the originally assigned default name when custom name is cleared
  if (block.defaultName && block.defaultName.trim()) {
    return truncateLabel(block.defaultName.trim());
  }

  return null;
}

interface ArchitectureBlockComponentProps {
  block: ArchitectureBlock;
  isSelected: boolean;
}

export default function ArchitectureBlockComponent({ block, isSelected }: ArchitectureBlockComponentProps) {
  const iconPath = getIconPath(block.serviceType);

  const { width, height } = block.visualConfig;

  const displayName = getBlockDisplayName(block);

  const { handleMouseDown, alignmentGuides, distributionGuides } = useSnapDrag({
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
        <div
          data-testid={`service-label-${block.id}`}
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            transform: `translate(${block.position.x - width / 2}px, ${block.position.y + height / 2 + GAP}px)`,
            width: `${width}px`,
            height: '16px',
            fontSize: '11px',
            lineHeight: '16px',
            color: '#ffffff',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            textAlign: 'center',
            pointerEvents: 'none',
          }}
        >
          {displayName}
        </div>
      )}
      {(alignmentGuides.length > 0 || distributionGuides.length > 0) && <AlignmentGuides guides={alignmentGuides} distributionGuides={distributionGuides} />}
    </>
  );
}
