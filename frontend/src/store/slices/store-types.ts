/**
 * The composed diagram store, assembled from its slices.
 */

import type { AnchoringSlice } from './anchoring-slice';
import type { CanvasSlice } from './canvas-slice';
import type { ClipboardSlice } from './clipboard-slice';
import type { ConnectorSlice } from './connector-slice';
import type { SemanticContainmentSlice } from './semantic-containment-slice';
import type { GroupingSlice } from './grouping-slice';
import type { HistorySlice } from './history-slice';
import type { PersistenceSlice } from './persistence-slice';
import type { ProjectSlice } from './project-slice';
import type { SerializationSlice } from './serialization-slice';
import type { UISlice } from './ui-slice';
import type { ViewportSlice } from './viewport-slice';
import type { ZOrderSlice } from './zorder-slice';

export type DiagramStore =
  AnchoringSlice
  & CanvasSlice
  & ClipboardSlice
  & ConnectorSlice
  & SemanticContainmentSlice
  & GroupingSlice
  & HistorySlice
  & PersistenceSlice
  & ProjectSlice
  & SerializationSlice
  & UISlice
  & ViewportSlice
  & ZOrderSlice;
