/**
 * Connector Slice — Connector CRUD and selection.
 *
 * This file defines the public contract (ConnectorSlice interface) for the
 * connector concerns of the diagram store. The actual implementation will be
 * extracted from diagram-store.ts in a subsequent pass (task 10.6).
 *
 * Requirements: 7.1, 7.8
 */

import type { StateCreator } from 'zustand';
import type { Connector } from '@/types/diagram';

export interface ConnectorSlice {
  connectors: Map<string, Connector>;
  selectedConnectorId: string | null;
  addConnector: (sourceId: string, targetId: string, connectionType: string) => string | null;
  removeConnector: (id: string) => void;
  selectConnector: (id: string | null) => void;
  updateConnectorConfig: (id: string, config: Record<string, unknown>) => void;
}

export type CreateConnectorSlice = StateCreator<ConnectorSlice, [], [], ConnectorSlice>;
