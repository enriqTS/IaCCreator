'use client';

import { useSnapDrag } from '@/hooks/useSnapDrag';
import AlignmentGuides from '@/components/canvas/AlignmentGuides';
import { SHAPE_PATH_REGISTRY } from '@/utils/shape-paths';
import { getShapeTightBounds } from '@/utils/bounds-utils';
import type { GeometricObject } from '@/types/diagram';

interface GeometricObjectComponentProps {
  object: GeometricObject;
  isSelected: boolean;
}

/** Minimum clickable stroke width for hollow objects (px) */
const MIN_STROKE_HIT_WIDTH = 8;

export default function GeometricObjectComponent({ object, isSelected }: GeometricObjectComponentProps) {
  const { width, height, fill, fillColor, borderColor, borderWidth, shape } = object.visualConfig;

  const { handleMouseDown, alignmentGuides } = useSnapDrag({
    objectId: object.id,
    isSelected,
    locked: object.locked,
  });

  // Get SVG path from registry, fall back to rectangle
  const pathFn = SHAPE_PATH_REGISTRY[shape] ?? SHAPE_PATH_REGISTRY['rectangle'];
  const pathD = pathFn(width, height);

  // Compute tight bounds for this shape (used for selection bounds positioning)
  const tightBounds = getShapeTightBounds(shape, width, height, borderWidth);

  const strokeColor = isSelected ? 'rgba(59, 130, 246, 0.8)' : borderColor;
  const fillValue = fill ? fillColor : 'transparent';
  const strokeHitWidth = Math.max(borderWidth, MIN_STROKE_HIT_WIDTH);

  return (
    <>
      <div
        data-testid={`geometric-object-${object.id}`}
        data-object-id={object.id}
        data-tight-bounds-x={tightBounds.x}
        data-tight-bounds-y={tightBounds.y}
        data-tight-bounds-width={tightBounds.width}
        data-tight-bounds-height={tightBounds.height}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          transform: `translate(${object.position.x - width / 2}px, ${object.position.y - height / 2}px)`,
          width: `${width}px`,
          height: `${height}px`,
          pointerEvents: 'none',
          userSelect: 'none',
        }}
      >
        {object.locked && (
          <span
            data-testid={`lock-badge-${object.id}`}
            style={{
              position: 'absolute',
              top: 2,
              right: 2,
              fontSize: '10px',
              lineHeight: 1,
              pointerEvents: 'none',
              zIndex: 1,
            }}
          >
            🔒
          </span>
        )}
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          style={{ position: 'absolute', inset: 0, overflow: 'visible' }}
        >
          {/* Invisible wider hit area for easier clicking */}
          <path
            d={pathD}
            fill={fill ? 'transparent' : 'none'}
            stroke="transparent"
            strokeWidth={strokeHitWidth}
            onMouseDown={handleMouseDown}
            style={{ pointerEvents: fill ? 'fill' : 'stroke', cursor: object.locked ? 'not-allowed' : 'grab' }}
          />
          {/* Visible shape */}
          <path
            d={pathD}
            fill={fillValue}
            stroke={strokeColor}
            strokeWidth={borderWidth}
            style={{ pointerEvents: fill ? 'auto' : 'none' }}
            onMouseDown={fill ? handleMouseDown : undefined}
          />
        </svg>
      </div>
      {alignmentGuides.length > 0 && <AlignmentGuides guides={alignmentGuides} />}
    </>
  );
}
