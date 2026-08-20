/**
 * The composed diagram store, assembled from its slices.
 */

import type { CanvasSlice } from './canvas-slice';
import type { ConnectorSlice } from './connector-slice';
import type { HistorySlice } from './history-slice';
import type { PersistenceSlice } from './persistence-slice';
import type { ProjectSlice } from './project-slice';
import type { SerializationSlice } from './serialization-slice';
import type { UISlice } from './ui-slice';
import type { ViewportSlice } from './viewport-slice';

export type DiagramStore =
  CanvasSlice
  & ConnectorSlice
  & HistorySlice
  & PersistenceSlice
  & ProjectSlice
  & SerializationSlice
  & UISlice
  & ViewportSlice;
