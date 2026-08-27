import type { StateCreator } from 'zustand';
import type { CanvasObject, Connector } from '@/types/diagram';
import { apiClient } from '@/utils/api-client';
import { normalizeSemanticZOrder } from '@/utils/semantic-containment';
import { useToastStore } from '@/store/toast-store';
import type { DiagramState } from '@/types/serialization';
import type { DiagramStore } from './store-types';

export interface SemanticContainmentSlice {
  pendingContainmentObjectId: string | null;
  activeContainmentTargetId: string | null;
  activeContainmentTargetValid: boolean | null;
  containmentDragStartParentId: string | null;
  beginContainmentDrag: (objectId: string) => void;
  updateContainmentTarget: (targetId: string | null, valid: boolean | null) => void;
  finishContainmentDrag: (objectId: string) => Promise<void>;
  setResourcePresentation: (objectId: string, presentation: 'node' | 'container') => Promise<void>;
}

function canonicalState(
  currentObjects: Map<string, CanvasObject>,
  diagram: DiagramState,
): Pick<DiagramStore, 'canvasObjects' | 'connectors'> {
  const objects = new Map(currentObjects);
  for (const serialized of diagram.canvasObjects ?? []) {
    const current = objects.get(serialized.id);
    if (!current) continue;
    const updates: Partial<CanvasObject> = {
      parentContainerId: serialized.parentContainerId ?? undefined,
    } as Partial<CanvasObject>;
    if (serialized.objectType === 'architecture-block' && current.objectType === 'architecture-block') {
      const presentation = serialized.presentation ?? 'node';
      Object.assign(updates, {
        presentation,
        config: { ...(serialized.config ?? {}) },
        visualConfig: presentation === 'container'
          ? {
              width: Math.max(current.visualConfig.width, 480),
              height: Math.max(current.visualConfig.height, 320),
            }
          : current.presentation === 'container'
            ? { width: 80, height: 80 }
            : current.visualConfig,
      });
    }
    objects.set(current.id, { ...current, ...updates } as CanvasObject);
  }
  const connectors = new Map<string, Connector>();
  for (const connector of diagram.connectors) {
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
  return { canvasObjects: normalizeSemanticZOrder(objects), connectors };
}

export const createSemanticContainmentSlice: StateCreator<DiagramStore, [], [], SemanticContainmentSlice> = (set, get) => ({
  pendingContainmentObjectId: null,
  activeContainmentTargetId: null,
  activeContainmentTargetValid: null,
  containmentDragStartParentId: null,

  beginContainmentDrag: (objectId) => {
    const object = get().canvasObjects.get(objectId);
    set({
      activeContainmentTargetId: null,
      activeContainmentTargetValid: null,
      containmentDragStartParentId: object && 'parentContainerId' in object
        ? object.parentContainerId ?? null
        : null,
    });
  },

  updateContainmentTarget: (targetId, valid) => {
    set({ activeContainmentTargetId: targetId, activeContainmentTargetValid: valid });
  },

  finishContainmentDrag: async (objectId) => {
    const state = get();
    const targetId = state.activeContainmentTargetId;
    const valid = state.activeContainmentTargetValid;
    const previousParentId = state.containmentDragStartParentId;
    set({
      activeContainmentTargetId: null,
      activeContainmentTargetValid: null,
      containmentDragStartParentId: null,
    });
    if (valid === false) {
      useToastStore.getState().addToast('This object cannot be placed in that container.', 'error');
      return;
    }
    if (targetId === previousParentId || (!targetId && !previousParentId)) return;
    if (get().pendingContainmentObjectId) return;

    set({ pendingContainmentObjectId: objectId });
    const dragged = get().canvasObjects.get(objectId);
    const movesSubtree = dragged?.objectType === 'semantic-container'
      || (dragged?.objectType === 'architecture-block' && dragged.presentation === 'container');
    const result = await apiClient.applyContainmentOperation(get().serializeDiagramState(), {
      operation: targetId ? (movesSubtree ? 'move-subtree' : 'assign') : 'remove',
      object_id: objectId,
      ...(targetId && { parent_id: targetId }),
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
    set((current) => ({
      ...canonicalState(current.canvasObjects, result.data.diagram),
      pendingContainmentObjectId: null,
    }));
  },

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
    set((current) => ({
      ...canonicalState(current.canvasObjects, result.data.diagram),
      pendingContainmentObjectId: null,
    }));
  },
});
