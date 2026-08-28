'use client';

import AlignmentGuides from '@/components/canvas/interactions/AlignmentGuides';
import { useSnapDrag } from '@/hooks/useSnapDrag';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock, SemanticContainerObject } from '@/types/diagram';

interface Props {
  object: SemanticContainerObject | ArchitectureBlock;
  isSelected: boolean;
}

export default function SemanticContainerComponent({ object, isSelected }: Props) {
  const { width, height } = object.visualConfig;
  const activeTargetId = useDiagramStore((state) => state.activeContainmentTargetId);
  const toggleCollapsed = useDiagramStore((state) => state.toggleContainerCollapsed);
  const activeTargetValid = useDiagramStore((state) => state.activeContainmentTargetValid);
  const isDropTarget = activeTargetId === object.id;
  const scope = object.objectType === 'semantic-container' ? object.containerType : object.serviceType;
  const fillColor = object.objectType === 'semantic-container' ? object.visualConfig.fillColor : '#0f2740';
  const borderColor = object.objectType === 'semantic-container' ? object.visualConfig.borderColor : '#4f8fbf';
  const borderWidth = object.objectType === 'semantic-container' ? object.visualConfig.borderWidth : 2;
  const { handleMouseDown, alignmentGuides, distributionGuides } = useSnapDrag({
    objectId: object.id,
    isSelected,
    locked: object.locked,
  });

  return (
    <>
      <div
        data-testid={`semantic-container-${object.id}`}
        data-object-id={object.id}
        data-container-type={scope}
        data-drop-target={isDropTarget ? (activeTargetValid ? 'valid' : 'invalid') : undefined}
        onMouseDown={handleMouseDown}
        style={{
          position: 'absolute',
          left: object.position.x - width / 2,
          top: object.position.y - height / 2,
          width,
          height: object.collapsed ? 34 : height,
          pointerEvents: 'auto',
          border: `${isDropTarget ? Math.max(3, borderWidth) : borderWidth}px ${scope === 'availability-zone' ? 'dashed' : 'solid'} ${isDropTarget ? (activeTargetValid ? '#22c55e' : '#ef4444') : isSelected ? '#60a5fa' : borderColor}`,
          background: isDropTarget ? (activeTargetValid ? '#14532d' : '#7f1d1d') : fillColor,
          borderRadius: 8,
          boxSizing: 'border-box',
          userSelect: 'none',
          opacity: 0.72,
          cursor: object.locked ? 'not-allowed' : 'grab',
        }}
      >
        <div
          style={{
            minHeight: 32,
            padding: '7px 12px',
            borderBottom: `1px solid ${borderColor}`,
            color: '#e2e8f0',
            fontSize: 12,
            fontWeight: 600,
            boxSizing: 'border-box',
          }}
        >
          <button
            type="button"
            aria-label={object.collapsed ? `Expand ${object.name}` : `Collapse ${object.name}`}
            onMouseDown={(event) => event.stopPropagation()}
            onClick={(event) => {
              event.stopPropagation();
              toggleCollapsed(object.id);
            }}
            style={{
              marginRight: 6,
              border: 0,
              padding: 0,
              color: 'inherit',
              background: 'transparent',
              cursor: 'pointer',
            }}
          >
            {object.collapsed ? '▸' : '▾'}
          </button>
          {object.name} · {scope}
          {object.locked && <span style={{ float: 'right' }}>🔒</span>}
        </div>
      </div>
      {(alignmentGuides.length > 0 || distributionGuides.length > 0) && (
        <AlignmentGuides guides={alignmentGuides} distributionGuides={distributionGuides} />
      )}
    </>
  );
}
