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

/** Fraction of the object's smaller side used for the anchor indicator diameter */
const ANCHOR_ZONE_RATIO = 0.2;
/** Minimum anchor indicator size in canvas pixels (prevents it from becoming too tiny) */
const ANCHOR_ZONE_MIN = 4;
/** Maximum anchor indicator size in canvas pixels (prevents it from becoming too large) */
const ANCHOR_ZONE_MAX = 24;

const ANCHOR_POSITIONS: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

export default function AnchorIndicators({ objectId, bounds, locked }: AnchorIndicatorsProps) {
  const setPullConnectState = useDiagramStore((s) => s.setPullConnectState);
  const scale = useDiagramStore((s) => s.viewport.scale);

  const anchors = getAnchorPoints(bounds);

  // Size proportional to the object's smaller side, clamped to min/max
  const smallerSide = Math.min(bounds.width, bounds.height);
  const zoneSize = Math.max(ANCHOR_ZONE_MIN, Math.min(ANCHOR_ZONE_MAX, smallerSide * ANCHOR_ZONE_RATIO));

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
            data-object-id={objectId}
            onMouseDown={(e) => handleMouseDown(e, point, pos)}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              transform: `translate(${point.x - zoneSize / 2}px, ${point.y - zoneSize / 2}px)`,
              width: zoneSize,
              height: zoneSize,
              pointerEvents: 'auto',
              zIndex: 10,
              cursor: 'crosshair',
              borderRadius: '50%',
              backgroundColor: 'rgba(34, 197, 94, 0.25)',
              border: `${Math.max(1, zoneSize * 0.08)}px solid rgba(34, 197, 94, 0.6)`,
              boxSizing: 'border-box',
            }}
          />
        );
      })}
    </>
  );
}
