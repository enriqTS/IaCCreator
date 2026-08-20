/**
 * Reading and writing diagrams on the server.
 */

import type { StateCreator } from 'zustand';
import { useToastStore } from '@/store/toast-store';
import type { DiagramSummary } from '@/types/api';
import type { DiagramState } from '@/types/serialization';
import { apiClient } from '@/utils/api-client';
import type { DiagramStore } from './store-types';

export interface PersistenceSlice {
  // Server persistence
  currentDiagramId: string | null;
  diagramSummaries: DiagramSummary[];
  isSaving: boolean;
  isLoading: boolean;
  saveDiagramToServer: () => Promise<void>;
  updateDiagramOnServer: (id: string) => Promise<void>;
  loadDiagramFromServer: (id: string) => Promise<void>;
  listDiagramsFromServer: () => Promise<DiagramSummary[]>;
  deleteDiagramFromServer: (id: string) => Promise<void>;
}

export const createPersistenceSlice: StateCreator<DiagramStore, [], [], PersistenceSlice> = (set, get) => ({
    // --- Server persistence ---
    currentDiagramId: null,
    diagramSummaries: [] as DiagramSummary[],
    isSaving: false,
    isLoading: false,

    saveDiagramToServer: async (): Promise<void> => {
      const toast = useToastStore.getState();
      set({ isSaving: true });
      try {
        const state = get().serializeDiagramState();
        const result = await apiClient.saveDiagram(state);
        if (result.ok) {
          set({ currentDiagramId: result.data.id });
          toast.addToast('Diagram saved', 'success');
        } else {
          toast.addToast(result.error.message, 'error');
        }
      } finally {
        set({ isSaving: false });
      }
    },

    updateDiagramOnServer: async (id: string): Promise<void> => {
      const toast = useToastStore.getState();
      set({ isSaving: true });
      try {
        const state = get().serializeDiagramState();
        const result = await apiClient.updateDiagram(id, state);
        if (result.ok) {
          toast.addToast('Diagram updated', 'success');
        } else {
          toast.addToast(result.error.message, 'error');
        }
      } finally {
        set({ isSaving: false });
      }
    },

    loadDiagramFromServer: async (id: string): Promise<void> => {
      const toast = useToastStore.getState();
      set({ isLoading: true });
      try {
        const result = await apiClient.loadDiagram(id);
        if (result.ok) {
          get().loadDiagramState(result.data as DiagramState);
          set({ currentDiagramId: id });
        } else {
          toast.addToast(result.error.message, 'error');
        }
      } finally {
        set({ isLoading: false });
      }
    },

    listDiagramsFromServer: async (): Promise<DiagramSummary[]> => {
      const toast = useToastStore.getState();
      set({ isLoading: true });
      try {
        const result = await apiClient.listDiagrams();
        if (result.ok) {
          set({ diagramSummaries: result.data });
          return result.data;
        } else {
          toast.addToast(result.error.message, 'error');
          return [];
        }
      } finally {
        set({ isLoading: false });
      }
    },

    deleteDiagramFromServer: async (id: string): Promise<void> => {
      const toast = useToastStore.getState();
      try {
        const result = await apiClient.deleteDiagram(id);
        if (result.ok) {
          toast.addToast('Diagram deleted', 'success');
          if (get().currentDiagramId === id) {
            set({ currentDiagramId: null });
          }
          set((state) => ({
            diagramSummaries: state.diagramSummaries.filter((s) => s.diagram_id !== id),
          }));
        } else {
          toast.addToast(result.error.message, 'error');
        }
      } catch {
        toast.addToast('Failed to delete diagram', 'error');
      }
    },
});
