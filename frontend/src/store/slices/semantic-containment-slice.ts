import type { StateCreator } from 'zustand';
import type { CanvasObject, Connector } from '@/types/diagram';
import { apiClient } from '@/utils/api-client';
import { normalizeSemanticZOrder } from '@/utils/semantic-containment';
import { useToastStore } from '@/store/toast-store';
import type { DiagramStore } from './store-types';

export interface SemanticContainmentSlice {
  pendingContainmentObjectId: string | null;
  setResourcePresentation: (objectId: string, presentation: 'node' | 'container') => Promise<void>;
}

export const createSemanticContainmentSlice: StateCreator<DiagramStore, [], [], SemanticContainmentSlice> = (set, get) => ({
  pendingContainmentObjectId: null,
  setResourcePresentation: async (objectId, presentation) => {
    if (get().pendingContainmentObjectId) return;
    set({ pendingContainmentObjectId: objectId });
    const result = await apiClient.applyContainmentOperation(get().serializeDiagramState(), {
      operation: 'set-presentation',
      object_id: objectId,
      presentation,
    });
    if (!result.ok) {
      set({ pendingContainmentObjectId: null });
      useToastStore.getState().addToast(result.error.message, 'error');
      return;
    }
    const issues = (result.data.resolution.issues as Array<{ severity: string; message: string }> | undefined) ?? [];
    const error = issues.find((issue) => issue.severity === 'error');
    if (error) {
      set({ pendingContainmentObjectId: null });
      useToastStore.getState().addToast(error.message, 'error');
      return;
    }

    get().pushHistory();
    set((state) => {
      const objects = new Map(state.canvasObjects);
      for (const serialized of result.data.diagram.canvasObjects ?? []) {
        const current = objects.get(serialized.id);
        if (!current) continue;
        const updates: Partial<CanvasObject> = {};
        if (serialized.parentContainerId !== undefined) Object.assign(updates, { parentContainerId: serialized.parentContainerId });
        if (serialized.objectType === 'architecture-block' && current.objectType === 'architecture-block') {
          const nextPresentation = serialized.presentation ?? 'node';
          Object.assign(updates, {
            presentation: nextPresentation,
            config: { ...(serialized.config ?? {}) },
            visualConfig: nextPresentation === 'container'
              ? {
                  width: Math.max(current.visualConfig.width, 480),
                  height: Math.max(current.visualConfig.height, 320),
                }
              : { width: 80, height: 80 },
          });
        }
        objects.set(current.id, { ...current, ...updates } as CanvasObject);
      }
      const connectors = new Map<string, Connector>();
      for (const connector of result.data.diagram.connectors) {
        connectors.set(connector.id, {
          id: connector.id,
          sourceId: connector.sourceId,
          targetId: connector.targetId,
          connectionType: connector.connectionType,
          ...(connector.connection_config && { connectionConfig: { ...connector.connection_config } }),
          origin: connector.origin ?? 'explicit',
          ...(connector.container_id && { containerId: connector.container_id }),
        });
      }
      return {
        canvasObjects: normalizeSemanticZOrder(objects),
        connectors,
        pendingContainmentObjectId: null,
      };
    });
  },
});
