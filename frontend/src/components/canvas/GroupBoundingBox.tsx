'use client';

import { useDiagramStore } from '@/store/diagram-store';
import { getObjectBounds } from '@/types/diagram';

interface GroupBoundingBoxProps {
  groupId: string;
}

const PADDING = 8;

export default function GroupBoundingBox({ groupId }: GroupBoundingBoxProps) {
  const group = useDiagramStore((s) => s.objectGroups.get(groupId));
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);

  if (!group || group.memberIds.length === 0) return null;

  // Collect bounds for all member objects
  const memberBounds = group.memberIds
    .map((id) => canvasObjects.get(id))
    .filter(Boolean)
    .map((obj) => getObjectBounds(obj!));

  if (memberBounds.length === 0) return null;

  // Compute union bounding box
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const b of memberBounds) {
    if (b.x < minX) minX = b.x;
    if (b.y < minY) minY = b.y;
    if (b.x + b.width > maxX) maxX = b.x + b.width;
    if (b.y + b.height > maxY) maxY = b.y + b.height;
  }

  return (
    <div
      data-testid={`group-bbox-${groupId}`}
      style={{
        position: 'absolute',
        left: minX - PADDING,
        top: minY - PADDING,
        width: maxX - minX + PADDING * 2,
        height: maxY - minY + PADDING * 2,
        border: '1.5px dashed rgba(99, 102, 241, 0.5)',
        borderRadius: 4,
        pointerEvents: 'none',
      }}
    />
  );
}
