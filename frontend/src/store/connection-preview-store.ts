/**
 * Connection preview store — asks the backend what each connection contributes.
 *
 * The judgement of what a connection generates, and of whether it is incomplete,
 * belongs to the backend; this store only caches the answer and keys it by connector.
 */

import { create } from 'zustand';
import type { ConnectionPreview } from '@/types/connection-preview';
import type { Connector } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';
import { apiClient } from '@/utils/api-client';

export type PreviewStatus = 'idle' | 'loading' | 'ready' | 'unavailable';

interface ConnectionPreviewState {
  previews: Map<string, ConnectionPreview>;
  status: PreviewStatus;
  /** Why the previews could not be produced, when the status is unavailable. */
  error: string | null;
  refresh: () => Promise<void>;
}

/** Match a preview to the connector it describes, whichever way the line was drawn. */
function matchConnector(
  preview: ConnectionPreview,
  connectors: Map<string, Connector>,
): string | null {
  for (const [id, connector] of connectors) {
    const sameIds =
      preview.source_id === connector.sourceId && preview.target_id === connector.targetId;
    if (sameIds && preview.connection_type === connector.connectionType) return id;
  }
  return null;
}

export const useConnectionPreviewStore = create<ConnectionPreviewState>()((set) => ({
  previews: new Map(),
  status: 'idle',
  error: null,

  refresh: async (): Promise<void> => {
    const store = useDiagramStore.getState();
    if (store.connectors.size === 0) {
      set({ previews: new Map(), status: 'ready', error: null });
      return;
    }

    set({ status: 'loading' });
    const result = await apiClient.previewConnections(
      store.serializeDiagramState(),
    );

    if (!result.ok) {
      set({ previews: new Map(), status: 'unavailable', error: result.error.message });
      return;
    }

    // Connectors may have changed while the request was in flight
    const connectors = useDiagramStore.getState().connectors;
    const byConnector = new Map<string, ConnectionPreview>();
    for (const preview of result.data.previews) {
      const connectorId = matchConnector(preview, connectors);
      if (connectorId) byConnector.set(connectorId, preview);
    }
    set({ previews: byConnector, status: 'ready', error: null });
  },
}));

/** The preview for one connector, or null while none has been fetched. */
export function useConnectionPreview(connectorId: string | null): ConnectionPreview | null {
  return useConnectionPreviewStore((s) =>
    connectorId ? s.previews.get(connectorId) ?? null : null,
  );
}
