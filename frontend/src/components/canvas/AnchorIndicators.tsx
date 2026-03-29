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
/** Invisible hit area radius — much larger than the visual dot for easier grabbing */
const HIT_RADIUS = 14;
const ANCHOR_COLOR = '#3b82f6';
const ANCHOR_STROKE = '#ffffff';

const ANCHOR_POSITIONS: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

export default function AnchorIndicators({ objectId, bounds, locked }: AnchorIndicatorsProps) {
  const setPullConnectState = useDiagramStore((s) => s.setPullConnectState);

  const anchors = getAnchorPoints(bounds);

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
              transform: `translate(${point.x - HIT_RADIUS}px, ${point.y - HIT_RADIUS}px)`,
              width: HIT_RADIUS * 2,
              height: HIT_RADIUS * 2,
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
                width: ANCHOR_RADIUS * 2,
                height: ANCHOR_RADIUS * 2,
                borderRadius: '50%',
                backgroundColor: ANCHOR_COLOR,
                border: `1.5px solid ${ANCHOR_STROKE}`,
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
