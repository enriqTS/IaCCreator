/**
 * Snapshot helpers shared by the history slice.
 */

import type { CanvasObject, Connector, ObjectGroup } from '@/types/diagram';

export interface HistoryEntry {
  connectors: Map<string, Connector>;
  canvasObjects: Map<string, CanvasObject>;
  objectGroups: Map<string, ObjectGroup>;
}

export const MAX_HISTORY = 50;

export function takeSnapshot(state: HistoryEntry): HistoryEntry {
  return {
    connectors: structuredClone(state.connectors),
    canvasObjects: structuredClone(state.canvasObjects),
    objectGroups: structuredClone(state.objectGroups),
  };
}
