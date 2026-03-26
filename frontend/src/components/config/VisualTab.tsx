'use client';

import type { CanvasObject } from '@/types/diagram';
import BlockVisualConfig from './BlockVisualConfig';
import LineVisualConfig from './LineVisualConfig';
import GeoVisualConfig from './GeoVisualConfig';

interface VisualTabProps {
  object: CanvasObject;
}

/** Dispatches to the type-specific visual config form based on the selected object type. */
export default function VisualTab({ object }: VisualTabProps) {
  switch (object.objectType) {
    case 'architecture-block':
      return <BlockVisualConfig object={object} />;
    case 'line':
      return <LineVisualConfig object={object} />;
    case 'geometric':
      return <GeoVisualConfig object={object} />;
    default:
      return null;
  }
}
