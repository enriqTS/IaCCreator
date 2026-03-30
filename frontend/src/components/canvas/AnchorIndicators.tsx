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

/** Screen-pixel size for the visible clickable anchor zone */
const ANCHOR_ZONE_SCREEN = 16;
/** Screen-pixel size for the center dot */
const DOT_SIZE_SCREEN = 8;

const ANCHOR_POSITIONS: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

export default function AnchorIndicators({ objectId, bounds, locked }: AnchorIndicatorsProps) {
  const setPullConnectState = useDiagramStore((s) => s.setPullConnectState);
  const scale = useDiagramStore((s) => s.viewport.scale);

  const anchors = getAnchorPoints(bounds);

  // Scale-compensated sizes so they stay constant in screen pixels
  const zoneSize = ANCHOR_ZONE_SCREEN / scale;
  const dotSize = DOT_SIZE_SCREEN / scale;
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
              transform: `translate(${point.x - zoneSize / 2}px, ${point.y - zoneSize / 2}px)`,
              width: zoneSize,
              height: zoneSize,
              borderRadius: `${3 / scale}px`,
              cursor: 'crosshair',
              pointerEvents: 'auto',
              zIndex: 10,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(34, 197, 94, 0.25)',
              border: `${borderWidth}px solid rgba(34, 197, 94, 0.6)`,
              boxSizing: 'border-box',
            }}
          >
            {/* Center dot */}
            <div
              style={{
                width: dotSize,
                height: dotSize,
                borderRadius: '50%',
                backgroundColor: 'rgba(34, 197, 94, 0.9)',
                pointerEvents: 'none',
              }}
            />
          </div>
        );
      })}
    </>
  );
}
