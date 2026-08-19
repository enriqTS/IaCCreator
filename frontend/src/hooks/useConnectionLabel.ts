/**
 * Hook that resolves the connection label and dashed state for a LineObject.
 *
 * Uses the diagram store to find the associated connector, then applies the
 * presentation rules for that connection kind.
 */

import { useMemo } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { findConnectorForLine } from '@/connections/connector-utils';
import { getPresentation } from '@/connections/presentation';
import type { LineObject } from '@/types/diagram';

interface ConnectionLabelResult {
  /** The label text to display, or null if no label should be shown */
  label: string | null;
  /** Whether the line should render with dashed stroke (overrides line's own strokeStyle) */
  dashed: boolean;
}

export function useConnectionLabel(line: LineObject): ConnectionLabelResult {
  const connectors = useDiagramStore((s) => s.connectors);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);

  return useMemo(() => {
    const connector = findConnectorForLine(line, connectors, canvasObjects);
    if (!connector) {
      return { label: null, dashed: false };
    }

    // No label when connectionConfig is empty or undefined
    const config = connector.connectionConfig;
    if (!config || Object.keys(config).length === 0) {
      return { label: null, dashed: false };
    }

    const source = canvasObjects.get(connector.sourceId);
    const target = canvasObjects.get(connector.targetId);
    if (
      source?.objectType !== 'architecture-block' ||
      target?.objectType !== 'architecture-block'
    ) {
      return { label: null, dashed: false };
    }

    const presentation = getPresentation(
      source.serviceType,
      target.serviceType,
      connector.connectionType,
    );
    if (!presentation) {
      return { label: null, dashed: false };
    }

    return {
      label: presentation.getLabel(config),
      dashed: presentation.getDashed ? presentation.getDashed(config) : false,
    };
  }, [line, connectors, canvasObjects]);
}
