/**
 * Hook that resolves the backend's verdict on a LineObject's connection.
 *
 * Whether a connection is incomplete is a generation question, so the backend
 * decides it; this only looks up the answer for the line being drawn.
 */

import { useMemo } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { useConnectionPreviewStore } from '@/store/connection-preview-store';
import { findConnectorForLine } from '@/connections/connector-utils';
import type { ConnectionIssue } from '@/types/connection-preview';
import type { LineObject } from '@/types/diagram';

export function useConnectionIssues(line: LineObject): ConnectionIssue[] {
  const connectors = useDiagramStore((s) => s.connectors);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const previews = useConnectionPreviewStore((s) => s.previews);

  return useMemo(() => {
    const connector = findConnectorForLine(line, connectors, canvasObjects);
    if (!connector) return [];
    return previews.get(connector.id)?.issues ?? [];
  }, [line, connectors, canvasObjects, previews]);
}
