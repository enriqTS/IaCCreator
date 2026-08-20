/**
 * The diagram store — a composition of the slices in ./slices.
 *
 * Each slice owns one concern and is typed against the whole store, so a slice
 * can read across boundaries without anything needing to know the assembly order.
 */

import { create } from 'zustand';

import { createCanvasSlice } from './slices/canvas-slice';
import { createConnectorSlice } from './slices/connector-slice';
import { createHistorySlice } from './slices/history-slice';
import { createPersistenceSlice } from './slices/persistence-slice';
import { createProjectSlice } from './slices/project-slice';
import { createSerializationSlice } from './slices/serialization-slice';
import { createUISlice } from './slices/ui-slice';
import { createViewportSlice } from './slices/viewport-slice';
import { createZOrderSlice } from './slices/zorder-slice';
import { createGroupingSlice } from './slices/grouping-slice';
import { createClipboardSlice } from './slices/clipboard-slice';
import { createAnchoringSlice } from './slices/anchoring-slice';
import type { DiagramStore } from './slices/store-types';

export type { DiagramStore };

export const useDiagramStore = create<DiagramStore>()((...args) => ({
  ...createCanvasSlice(...args),
  ...createAnchoringSlice(...args),
  ...createClipboardSlice(...args),
  ...createGroupingSlice(...args),
  ...createZOrderSlice(...args),
  ...createConnectorSlice(...args),
  ...createHistorySlice(...args),
  ...createPersistenceSlice(...args),
  ...createProjectSlice(...args),
  ...createSerializationSlice(...args),
  ...createUISlice(...args),
  ...createViewportSlice(...args),
}));
