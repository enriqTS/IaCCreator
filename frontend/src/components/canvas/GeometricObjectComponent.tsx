'use client';

import { useDiagramStore } from '@/store/diagram-store';
import { canvasToScreen } from '@/utils/viewport';
import type { GeometricObject } from '@/types/diagram';

interface GeometricObjectComponentProps {
  object: GeometricObject;
  isSelected: boolean;
}

export default function GeometricObjectComponent({ object, isSelected }: GeometricObjectComponentProps) {
  const viewport = useDiagramStore((s) => s.viewport);
  const selectObject = useDiagramStore((s) => s.selectObject);

  const { width, height, fill, fillColor, borderColor, borderWidth, shape } = object.visualConfig;
  const screenPos = canvasToScreen(object.position, viewport);

  const scaledWidth = width * viewport.scale;
  const scaledHeight = height * viewport.scale;
  const scaledBorderWidth = borderWidth * viewport.scale;

  const backgroundColor = fill ? fillColor : 'transparent';
  const borderRadius = shape === 'ellipse' ? '50%' : '0px';

  const borderStyle = isSelected
    ? `${scaledBorderWidth}px solid rgba(59, 130, 246, 0.8)`
    : `${scaledBorderWidth}px solid ${borderColor}`;

  return (
    <div
      data-testid={`geometric-object-${object.id}`}
      onClick={(e) => {
        e.stopPropagation();
        selectObject(object.id);
      }}
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        transform: `translate(${screenPos.x - scaledWidth / 2}px, ${screenPos.y - scaledHeight / 2}px)`,
        width: `${scaledWidth}px`,
        height: `${scaledHeight}px`,
        backgroundColor,
        border: borderStyle,
        borderRadius,
        boxSizing: 'border-box',
        pointerEvents: 'auto',
        cursor: 'grab',
        userSelect: 'none',
      }}
    />
  );
}
