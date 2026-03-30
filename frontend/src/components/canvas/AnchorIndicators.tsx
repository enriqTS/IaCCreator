'use client';

import { useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { getAnchorPoints } from '@/utils/anchor';
import type { Rect, Point } from '@/types/diagram';
import type { AnchorPosition } from '@/utils/anchor';

interface AnchorIndicatorsProps {
  objectId: string;
  bounds: Rect;
  locked?: boolean;
}

const ANCHOR_RADIUS = 5;
/** Desired screen-pixel radius for the invisible hit area */
const HIT_RADIUS_SCREEN = 20;
/** Desired screen-pixel size for the visual anchor marker */
const MARKER_SIZE_SCREEN = 10;
const ANCHOR_COLOR = 'rgba(59, 130, 246, 0.7)';
const ANCHOR_HOVER_COLOR = 'rgba(34, 197, 94, 0.9)';
const ANCHOR_STROKE = '#ffffff';

const ANCHOR_POSITIONS: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

export default function AnchorIndicators({ objectId, bounds, locked }: AnchorIndicatorsProps) {
  const setPullConnectState = useDiagramStore((s) => s.setPullConnectState);
  const scale = useDiagramStore((s) => s.viewport.scale);

  const anchors = getAnchorPoints(bounds);

  // Scale-compensated sizes so they stay constant in screen pixels
  const hitRadius = HIT_RADIUS_SCREEN / scale;
  const markerSize = MARKER_SIZE_SCREEN / scale;
  const borderWidth = 1.5 / scale;

  const handleMouseDown = useCallback(
    (e: React.MouseEvent, anchorPoint: Point, anchorPos: AnchorPosition) => {
      if (locked) return;
      e.stopPropagation();
      e.preventDefault();
      setPullConnectState({ sourceObjectId: objectId, sourceAnchorPoint: anchorPoint, sourceAnchorPosition: anchorPos });
    },
    [objectId, locked, setPullConnectState],
  );

  if (locked) return null;

  return (
    <>
      {ANCHOR_POSITIONS.map((pos) => {
        const point = anchors[pos];
        return (
          <div
            key={pos}
            data-testid={`anchor-indicator-${objectId}-${pos}`}
            onMouseDown={(e) => handleMouseDown(e, point, pos)}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              transform: `translate(${point.x - hitRadius}px, ${point.y - hitRadius}px)`,
              width: hitRadius * 2,
              height: hitRadius * 2,
              borderRadius: '50%',
              cursor: 'crosshair',
              pointerEvents: 'auto',
              zIndex: 10,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* Visual marker — larger and more visible */}
            <div
              style={{
                width: markerSize,
                height: markerSize,
                borderRadius: '50%',
                backgroundColor: ANCHOR_COLOR,
                border: `${borderWidth}px solid ${ANCHOR_STROKE}`,
                boxSizing: 'border-box',
                pointerEvents: 'none',
                transition: 'background-color 0.1s',
              }}
              className="group-hover:bg-green-500"
            />
          </div>
        );
      })}
    </>
  );
}
