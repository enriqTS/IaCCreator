/**
 * History Slice — Undo/redo stack management.
 *
 * This file defines the public contract (HistorySlice interface) for the
 * history concerns of the diagram store. The actual implementation will be
 * extracted from diagram-store.ts in a subsequent pass (task 10.6).
 *
 * Requirements: 7.1, 7.4
 */

import type { StateCreator } from 'zustand';
import type { CanvasObject, Connector, ObjectGroup } from '@/types/diagram';

interface HistoryEntry {
  connectors: Map<string, Connector>;
  canvasObjects: Map<string, CanvasObject>;
  objectGroups: Map<string, ObjectGroup>;
}

export interface HistorySlice {
  undoStack: HistoryEntry[];
  redoStack: HistoryEntry[];
  pushHistory: () => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  clearHistory: () => void;
}

export type CreateHistorySlice = StateCreator<HistorySlice, [], [], HistorySlice>;
