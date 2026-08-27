'use client';

import type { SemanticContainerObject } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';

interface Props {
  object: SemanticContainerObject;
  isSelected: boolean;
}

export default function SemanticContainerComponent({ object, isSelected }: Props) {
  const selectObject = useDiagramStore((state) => state.selectObject);
  const { width, height, fillColor, borderColor, borderWidth } = object.visualConfig;

  return (
    <div
      data-object-id={object.id}
      onPointerDown={(event) => {
        event.stopPropagation();
        selectObject(object.id);
      }}
      style={{
        position: 'absolute',
        left: object.position.x - width / 2,
        top: object.position.y - height / 2,
        width,
        height,
        pointerEvents: object.locked ? 'none' : 'auto',
        border: `${borderWidth}px solid ${isSelected ? '#60a5fa' : borderColor}`,
        background: fillColor,
        opacity: 0.7,
        borderRadius: 8,
        boxSizing: 'border-box',
      }}
    >
      <div style={{ padding: '8px 12px', color: '#e2e8f0', fontSize: 12, fontWeight: 600 }}>
        {object.name} · {object.containerType}
      </div>
    </div>
  );
}
