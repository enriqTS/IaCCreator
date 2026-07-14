/**
 * Hook that computes bounding rectangles for all visible service name labels.
 *
 * Used by LineObjectComponent to add knockout mask rectangles that occlude
 * connection lines behind service name labels.
 */

import { useMemo } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { getBlockDisplayName } from '@/components/canvas/objects/ArchitectureBlockComponent';
import type { ArchitectureBlock } from '@/types/diagram';

/** Vertical gap between block bottom edge and label top (px) */
export const GAP = 6;

/** Approximate height of the 11px label text line (px) */
export const LABEL_HEIGHT = 14;

/** Horizontal padding for the knockout mask (px) */
export const H_PAD = 8;

/** Vertical padding for the knockout mask (px) */
export const V_PAD = 4;

export interface LabelRect {
  /** Block id */
  id: string;
  /** Left edge of mask rect */
  x: number;
  /** Top edge of mask rect */
  y: number;
  /** Mask rect width */
  width: number;
  /** Mask rect height */
  height: number;
}

/**
 * Returns bounding rectangles for all visible service name labels.
 * Used by LineObjectComponent to add knockout masks.
 */
export function useServiceNameLabels(): LabelRect[] {
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);

  return useMemo(() => {
    const rects: LabelRect[] = [];

    for (const obj of canvasObjects.values()) {
      if (obj.objectType !== 'architecture-block') continue;
      if (!getBlockDisplayName(obj as ArchitectureBlock)) continue;

      const { width, height } = obj.visualConfig;

      rects.push({
        id: obj.id,
        x: obj.position.x - width / 2 - H_PAD,
        y: obj.position.y + height / 2 + GAP - V_PAD,
        width: width + 2 * H_PAD,
        height: LABEL_HEIGHT + 2 * V_PAD,
      });
    }

    return rects;
  }, [canvasObjects]);
}
