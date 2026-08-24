/**
 * Keeps the connection previews in step with the diagram, debounced so typing
 * in a config form does not fire a request per keystroke.
 */

import { useEffect } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { useConnectionPreviewStore } from '@/store/connection-preview-store';

const DEBOUNCE_MS = 800;

export function useConnectionPreviewSync(delayMs: number = DEBOUNCE_MS): void {
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const connectors = useDiagramStore((s) => s.connectors);
  const refresh = useConnectionPreviewStore((s) => s.refresh);

  useEffect(() => {
    const timer = setTimeout(() => {
      void refresh();
    }, delayMs);
    return () => clearTimeout(timer);
  }, [canvasObjects, connectors, refresh, delayMs]);
}
