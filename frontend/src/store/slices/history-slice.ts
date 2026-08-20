/**
 * Undo and redo over canvas objects, connectors and groups.
 */

import type { StateCreator } from 'zustand';
import type { DiagramStore } from './store-types';
import { MAX_HISTORY, takeSnapshot } from './history-support';
import type { HistoryEntry } from './history-support';

export interface HistorySlice {
  // History (undo/redo)
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  beginDragGesture: () => void;

  /** @internal — exposed for testing reset only */
  _undoStack: HistoryEntry[];
  _redoStack: HistoryEntry[];

  /** @internal — records a snapshot before a mutating action */
  pushHistory: () => void;
}

export const createHistorySlice: StateCreator<DiagramStore, [], [], HistorySlice> = (set, get) => ({
    // --- History (undo/redo) ---
    pushHistory: (): void => {
      const { connectors, canvasObjects, objectGroups, _undoStack } = get();
      const snapshot = takeSnapshot({ connectors, canvasObjects, objectGroups });
      let newStack = [..._undoStack, snapshot];
      if (newStack.length > MAX_HISTORY) {
        newStack = newStack.slice(newStack.length - MAX_HISTORY);
      }
      set({ _undoStack: newStack, _redoStack: [], canUndo: true, canRedo: false });
    },

    canUndo: false,
    canRedo: false,
    _undoStack: [],
    _redoStack: [],

    undo: (): void => {
      const { _undoStack, _redoStack, connectors, canvasObjects, objectGroups } = get();
      if (_undoStack.length === 0) return;
      const currentSnapshot = takeSnapshot({ connectors, canvasObjects, objectGroups });
      const newRedoStack = [..._redoStack, currentSnapshot];

      const previous = _undoStack[_undoStack.length - 1];
      const newUndoStack = _undoStack.slice(0, -1);

      set({
        connectors: structuredClone(previous.connectors),
        canvasObjects: structuredClone(previous.canvasObjects),
        objectGroups: structuredClone(previous.objectGroups),
        _undoStack: newUndoStack,
        _redoStack: newRedoStack,
        canUndo: newUndoStack.length > 0,
        canRedo: true,
      });
    },

    redo: (): void => {
      const { _undoStack, _redoStack, connectors, canvasObjects, objectGroups } = get();
      if (_redoStack.length === 0) return;
      const currentSnapshot = takeSnapshot({ connectors, canvasObjects, objectGroups });
      const newUndoStack = [..._undoStack, currentSnapshot];

      const next = _redoStack[_redoStack.length - 1];
      const newRedoStack = _redoStack.slice(0, -1);

      set({
        connectors: structuredClone(next.connectors),
        canvasObjects: structuredClone(next.canvasObjects),
        objectGroups: structuredClone(next.objectGroups),
        _undoStack: newUndoStack,
        _redoStack: newRedoStack,
        canUndo: true,
        canRedo: newRedoStack.length > 0,
      });
    },

    beginDragGesture: (): void => {
      get().pushHistory();
    },
});
