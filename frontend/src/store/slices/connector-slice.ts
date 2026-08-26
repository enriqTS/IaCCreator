/**
 * Connectors between architecture blocks, and the entries they link to.
 */

import type { StateCreator } from 'zustand';
import type { Connector } from '@/types/diagram';
import { v4 as uuidv4 } from 'uuid';
import { apiClient } from '@/utils/api-client';
import { useToastStore } from '@/store/toast-store';
import type { DiagramStore } from './store-types';

let connectionOperationQueue: Promise<void> = Promise.resolve();

function queueConnectionOperation<T>(operation: () => Promise<T>): Promise<T> {
  const result = connectionOperationQueue.then(operation, operation);
  connectionOperationQueue = result.then(() => undefined, () => undefined);
  return result;
}

export interface ConnectorSlice {
  // Connector state
  connectors: Map<string, Connector>;
  addConnector: (sourceId: string, targetId: string, connectionType?: string, connectionConfig?: Record<string, string | number | boolean>) => string;
  updateConnectorType: (id: string, connectionType: string) => void;
  removeConnector: (id: string) => void;
  updateConnectorConfig: (id: string, key: string, value: string | number | boolean) => void;
  removeConnectorConfigKeys: (id: string, keys: string[]) => void;
  updateConnectorConfigBatch: (id: string, updates: Record<string, string | number | boolean>) => void;

  // Linked entry actions (atomic block + connector updates)
  createLinkedEntry: (
    blockId: string,
    configPath: string,
    newEntry: Record<string, unknown>,
    connectorId: string,
    connectorConfigKey: string,
    connectorConfigValue: string,
  ) => Promise<void>;
  removeLinkedEntry: (
    blockId: string,
    configPath: string,
    displayKey: string,
    removedValue: string,
    connectorConfigKey: string,
  ) => Promise<void>;
  updateLinkedEntry: (
    blockId: string,
    configPath: string,
    displayKey: string,
    entryValue: string,
    fieldKey: string,
    fieldValue: unknown,
    connectorId: string,
    connectionFieldKey: string,
  ) => Promise<void>;
}

export const createConnectorSlice: StateCreator<DiagramStore, [], [], ConnectorSlice> = (set, get) => ({
    // --- Connector state (initialized here for use by element-less store) ---
    connectors: new Map<string, Connector>(),

    // --- Connector state ---
    // NOTE: The Connector tool intentionally requires both a source and target Architecture_Block.
    // It uses orthogonal routing by default (via DEFAULT_LINE_VISUAL / globalRoutingMode).
    // This differs from Object Picker line/arrow placement which allows freeform (diagonal)
    // placement on the canvas without requiring connection to existing blocks.
    // (Satisfies Requirements 3.2 and 4.3)

    addConnector: (sourceId: string, targetId: string, connectionType?: string, connectionConfig?: Record<string, string | number | boolean>): string => {
      if (sourceId === targetId) {
        throw new Error('Cannot create a connector from an element to itself');
      }

      const { canvasObjects } = get();
      const sourceExists =
        (canvasObjects.has(sourceId) && canvasObjects.get(sourceId)!.objectType === 'architecture-block');
      const targetExists =
        (canvasObjects.has(targetId) && canvasObjects.get(targetId)!.objectType === 'architecture-block');

      if (!sourceExists) {
        throw new Error(`Source element ${sourceId} does not exist`);
      }
      if (!targetExists) {
        throw new Error(`Target element ${targetId} does not exist`);
      }

      get().pushHistory();

      const id = uuidv4();
      const connector: Connector = {
        id,
        sourceId,
        targetId,
        connectionType: connectionType ?? 'triggers',
        ...(connectionConfig !== undefined && { connectionConfig }),
      };

      set((state) => {
        const next = new Map(state.connectors);
        next.set(id, connector);
        return { connectors: next };
      });

      void queueConnectionOperation(() =>
        apiClient.normalizeDiagram(get().serializeDiagramState()),
      ).then((result) => {
        if (!result.ok) {
          set((state) => {
            const connectors = new Map(state.connectors);
            connectors.delete(id);
            return { connectors };
          });
          useToastStore.getState().addToast(result.error.message, 'error');
          return;
        }
        const canonical = result.data.connectors.find((item) => item.id === id);
        if (!canonical) return;
        set((state) => {
          const current = state.connectors.get(id);
          if (!current) return state;
          const connectors = new Map(state.connectors);
          connectors.set(id, {
            ...current,
            sourceId: canonical.sourceId,
            targetId: canonical.targetId,
            connectionType: canonical.connectionType,
            connectionConfig: canonical.connection_config,
          });
          return { connectors };
        });
      });

      return id;
    },

    updateConnectorType: (id: string, connectionType: string): void => {
      const conn = get().connectors.get(id);
      if (!conn) return;
      get().pushHistory();
      set((state) => {
        const next = new Map(state.connectors);
        next.set(id, { ...state.connectors.get(id)!, connectionType });
        return { connectors: next };
      });
    },

    removeConnector: (id: string): void => {
      if (!get().connectors.has(id)) return;

      get().pushHistory();

      set((state) => {
        const next = new Map(state.connectors);
        next.delete(id);
        return { connectors: next };
      });
    },

    updateConnectorConfig: (id: string, key: string, value: string | number | boolean): void => {
      const conn = get().connectors.get(id);
      if (!conn) return;
      get().pushHistory();
      set((state) => {
        const current = state.connectors.get(id)!;
        const next = new Map(state.connectors);
        next.set(id, {
          ...current,
          connectionConfig: { ...current.connectionConfig, [key]: value },
        });
        return { connectors: next };
      });
    },

    removeConnectorConfigKeys: (id: string, keys: string[]): void => {
      const conn = get().connectors.get(id);
      if (!conn) return;
      get().pushHistory();
      set((state) => {
        const current = state.connectors.get(id)!;
        const next = new Map(state.connectors);
        const updatedConfig = { ...current.connectionConfig };
        for (const key of keys) {
          delete updatedConfig[key];
        }
        next.set(id, { ...current, connectionConfig: updatedConfig });
        return { connectors: next };
      });
    },

    updateConnectorConfigBatch: (id: string, updates: Record<string, string | number | boolean>): void => {
      const conn = get().connectors.get(id);
      if (!conn) return;
      get().pushHistory();
      set((state) => {
        const current = state.connectors.get(id)!;
        const next = new Map(state.connectors);
        next.set(id, {
          ...current,
          connectionConfig: { ...current.connectionConfig, ...updates },
        });

        return { connectors: next };
      });
    },

    // --- Linked entry actions ---
    createLinkedEntry: async (
      blockId: string,
      configPath: string,
      newEntry: Record<string, unknown>,
      connectorId: string,
      connectorConfigKey: string,
      connectorConfigValue: string,
    ): Promise<void> => {
      const block = get().canvasObjects.get(blockId);
      if (!block || block.objectType !== 'architecture-block') return;
      if (!get().connectors.has(connectorId)) return;
      const result = await queueConnectionOperation(() =>
        apiClient.applyConnectionOperation(get().serializeDiagramState(), {
          operation: 'create', connector_id: connectorId, field_key: connectorConfigKey,
          display_value: connectorConfigValue, entry_values: newEntry,
        }),
      );
      if (!result.ok) {
        useToastStore.getState().addToast(result.error.message, 'error');
        return;
      }
      get().pushHistory();
      const canonicalBlock = result.data.canvasObjects?.find((item) => item.id === blockId);
      const canonicalConnector = result.data.connectors.find((item) => item.id === connectorId);
      set((state) => {
        const canvasObjects = new Map(state.canvasObjects);
        const connectors = new Map(state.connectors);
        const currentBlock = canvasObjects.get(blockId);
        const currentConnector = connectors.get(connectorId);
        if (canonicalBlock?.config && currentBlock?.objectType === 'architecture-block') {
          canvasObjects.set(blockId, {
            ...currentBlock,
            config: {
              ...currentBlock.config,
              [configPath]: (canonicalBlock.config as Record<string, unknown>)[configPath],
            },
          });
        }
        if (canonicalConnector && currentConnector) {
          connectors.set(connectorId, {
            ...currentConnector,
            connectionConfig: canonicalConnector.connection_config,
          });
        }
        return { canvasObjects, connectors };
      });
    },

    updateLinkedEntry: async (
      blockId: string,
      configPath: string,
      displayKey: string,
      entryValue: string,
      fieldKey: string,
      fieldValue: unknown,
      connectorId: string,
      connectionFieldKey: string,
    ): Promise<void> => {
      const connector = get().connectors.get(connectorId);
      if (!connector || connector.sourceId !== blockId) return;
      const result = await queueConnectionOperation(() =>
        apiClient.applyConnectionOperation(get().serializeDiagramState(), {
          operation: 'update', connector_id: connector.id, field_key: connectionFieldKey,
          display_value: entryValue, entry_field_key: fieldKey, entry_field_value: fieldValue,
        }),
      );
      if (!result.ok) {
        useToastStore.getState().addToast(result.error.message, 'error');
        return;
      }
      const canonicalBlock = result.data.canvasObjects?.find((item) => item.id === blockId);
      if (!canonicalBlock?.config) return;
      get().pushHistory();
      set((state) => {
        const canvasObjects = new Map(state.canvasObjects);
        const current = canvasObjects.get(blockId);
        if (current?.objectType === 'architecture-block') {
          canvasObjects.set(blockId, {
            ...current,
            config: {
              ...current.config,
              [configPath]: (canonicalBlock.config! as Record<string, unknown>)[configPath],
            },
          });
        }
        return { canvasObjects };
      });
    },

    removeLinkedEntry: async (
      blockId: string,
      configPath: string,
      displayKey: string,
      removedValue: string,
      connectorConfigKey: string,
    ): Promise<void> => {
      const block = get().canvasObjects.get(blockId);
      if (!block || block.objectType !== 'architecture-block') return;
      const result = await queueConnectionOperation(() =>
        apiClient.applyConnectionOperation(get().serializeDiagramState(), {
          operation: 'remove', source_block_id: blockId, field_key: connectorConfigKey,
          display_value: removedValue,
        }),
      );
      if (!result.ok) {
        useToastStore.getState().addToast(result.error.message, 'error');
        return;
      }
      get().pushHistory();
      const canonicalBlock = result.data.canvasObjects?.find((item) => item.id === blockId);
      set((state) => {
        const canvasObjects = new Map(state.canvasObjects);
        const connectors = new Map(state.connectors);
        const currentBlock = canvasObjects.get(blockId);
        if (canonicalBlock?.config && currentBlock?.objectType === 'architecture-block') {
          canvasObjects.set(blockId, {
            ...currentBlock,
            config: {
              ...currentBlock.config,
              [configPath]: (canonicalBlock.config as Record<string, unknown>)[configPath],
            },
          });
        }
        for (const canonical of result.data.connectors) {
          const current = connectors.get(canonical.id);
          if (current) {
            connectors.set(canonical.id, {
              ...current,
              connectionConfig: canonical.connection_config,
            });
          }
        }
        return { canvasObjects, connectors };
      });
    },
});
