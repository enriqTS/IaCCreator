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
const HIT_RADIUS_SCREEN = 24;
/** Desired screen-pixel radius for the visual dot */
const DOT_RADIUS_SCREEN = 5;
const ANCHOR_COLOR = '#3b82f6';
const ANCHOR_STROKE = '#ffffff';

const ANCHOR_POSITIONS: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

export default function AnchorIndicators({ objectId, bounds, locked }: AnchorIndicatorsProps) {
  const setPullConnectState = useDiagramStore((s) => s.setPullConnectState);
  const scale = useDiagramStore((s) => s.viewport.scale);

  const anchors = getAnchorPoints(bounds);

  // Scale-compensated radii so they stay constant in screen pixels
  const hitRadius = HIT_RADIUS_SCREEN / scale;
  const dotRadius = DOT_RADIUS_SCREEN / scale;
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
            {/* Visual dot */}
            <div
              style={{
                width: dotRadius * 2,
                height: dotRadius * 2,
                borderRadius: '50%',
                backgroundColor: ANCHOR_COLOR,
                border: `${borderWidth}px solid ${ANCHOR_STROKE}`,
                boxSizing: 'border-box',
                pointerEvents: 'none',
              }}
            />
          </div>
        );
      })}
    </>
  );
}
