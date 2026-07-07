/**
 * Persistence Slice — Save, load, list, and delete diagrams.
 *
 * This file defines the public contract (PersistenceSlice interface) for the
 * persistence concerns of the diagram store. The actual implementation will be
 * extracted from diagram-store.ts in a subsequent pass (task 10.6).
 *
 * Requirements: 7.1, 7.8
 */

import type { StateCreator } from 'zustand';
import type { DiagramState } from '@/types/serialization';
import type { DiagramSummary } from '@/types/api';

export interface PersistenceSlice {
  currentDiagramId: string | null;
  isLoading: boolean;
  isSaving: boolean;
  diagrams: DiagramSummary[];
  saveDiagram: () => Promise<void>;
  loadDiagram: (id: string) => Promise<void>;
  listDiagrams: () => Promise<void>;
  deleteDiagram: (id: string) => Promise<void>;
  createNewDiagram: () => void;
  serializeDiagramState: () => DiagramState;
  loadDiagramState: (state: DiagramState) => void;
}

export type CreatePersistenceSlice = StateCreator<PersistenceSlice, [], [], PersistenceSlice>;
