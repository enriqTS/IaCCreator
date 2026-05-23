/**
 * Hook that resolves the connection label and dashed state for a LineObject.
 *
 * Uses the diagram store to find the associated connector and schema,
 * then computes the label text and whether the line should be dashed.
 */

import { useMemo } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { findConnectorForLine, getSchemaForConnector } from '@/utils/connector-utils';
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

    const schema = getSchemaForConnector(connector, canvasObjects);
    if (!schema) {
      return { label: null, dashed: false };
    }

    const label = schema.getLabel(config);
    const dashed = schema.getDashed ? schema.getDashed(config) : false;

    return { label, dashed };
  }, [line, connectors, canvasObjects]);
}
