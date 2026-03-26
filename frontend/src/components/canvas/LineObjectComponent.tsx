'use client';

import { useDiagramStore } from '@/store/diagram-store';
import { canvasToScreen } from '@/utils/viewport';
import type { LineObject } from '@/types/diagram';

interface LineObjectComponentProps {
  line: LineObject;
  isSelected: boolean;
}

export default function LineObjectComponent({ line, isSelected }: LineObjectComponentProps) {
  const viewport = useDiagramStore((s) => s.viewport);
  const selectObject = useDiagramStore((s) => s.selectObject);

  const screenStart = canvasToScreen(line.start, viewport);
  const screenEnd = canvasToScreen(line.end, viewport);

  const { color, borderWidth, strokeStyle, startArrow, endArrow } = line.visualConfig;

  const scaledStrokeWidth = borderWidth * viewport.scale;
  const markerId = `line-${line.id}`;
  const startMarkerId = `${markerId}-start`;
  const endMarkerId = `${markerId}-end`;

  const dashArray = strokeStyle === 'dashed' ? `${scaledStrokeWidth * 3} ${scaledStrokeWidth * 2}` : undefined;

  // Arrowhead size scales with stroke width
  const arrowSize = Math.max(scaledStrokeWidth * 3, 6);

  return (
    <g data-testid={`line-object-${line.id}`} style={{ pointerEvents: 'auto', cursor: 'pointer' }}>
      <defs>
        {startArrow && (
          <marker
            id={startMarkerId}
            markerWidth={arrowSize}
            markerHeight={arrowSize}
            refX={arrowSize}
            refY={arrowSize / 2}
            orient="auto-start-reverse"
            markerUnits="userSpaceOnUse"
          >
            <path
              d={`M ${arrowSize} 0 L 0 ${arrowSize / 2} L ${arrowSize} ${arrowSize}`}
              fill="none"
              stroke={color}
              strokeWidth={Math.max(scaledStrokeWidth * 0.6, 1)}
            />
          </marker>
        )}
        {endArrow && (
          <marker
            id={endMarkerId}
            markerWidth={arrowSize}
            markerHeight={arrowSize}
            refX={0}
            refY={arrowSize / 2}
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <path
              d={`M 0 0 L ${arrowSize} ${arrowSize / 2} L 0 ${arrowSize}`}
              fill="none"
              stroke={color}
              strokeWidth={Math.max(scaledStrokeWidth * 0.6, 1)}
            />
          </marker>
        )}
      </defs>

      {/* Invisible wider hit area for easier clicking */}
      <line
        x1={screenStart.x}
        y1={screenStart.y}
        x2={screenEnd.x}
        y2={screenEnd.y}
        stroke="transparent"
        strokeWidth={Math.max(scaledStrokeWidth + 10, 12)}
        onClick={(e) => {
          e.stopPropagation();
          selectObject(line.id);
        }}
      />

      {/* Selection highlight glow */}
      {isSelected && (
        <line
          x1={screenStart.x}
          y1={screenStart.y}
          x2={screenEnd.x}
          y2={screenEnd.y}
          stroke="rgba(59, 130, 246, 0.5)"
          strokeWidth={scaledStrokeWidth + 6}
          strokeLinecap="round"
        />
      )}

      {/* Main visible line */}
      <line
        x1={screenStart.x}
        y1={screenStart.y}
        x2={screenEnd.x}
        y2={screenEnd.y}
        stroke={color}
        strokeWidth={scaledStrokeWidth}
        strokeDasharray={dashArray}
        strokeLinecap="round"
        markerStart={startArrow ? `url(#${startMarkerId})` : undefined}
        markerEnd={endArrow ? `url(#${endMarkerId})` : undefined}
      />
    </g>
  );
}
