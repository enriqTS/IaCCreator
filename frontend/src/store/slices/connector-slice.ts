/**
 * Connectors between architecture blocks, and the entries they link to.
 */

import type { StateCreator } from 'zustand';
import type { ArchitectureBlock, Connector, ResourceConfig } from '@/types/diagram';
import { v4 as uuidv4 } from 'uuid';
import type { DiagramStore } from './store-types';

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
  ) => void;
  removeLinkedEntry: (
    blockId: string,
    configPath: string,
    displayKey: string,
    removedValue: string,
    connectorConfigKey: string,
  ) => void;
  updateLinkedEntry: (
    blockId: string,
    configPath: string,
    displayKey: string,
    entryValue: string,
    fieldKey: string,
    fieldValue: unknown,
  ) => void;
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
    createLinkedEntry: (
      blockId: string,
      configPath: string,
      newEntry: Record<string, unknown>,
      connectorId: string,
      connectorConfigKey: string,
      connectorConfigValue: string,
    ): void => {
      const block = get().canvasObjects.get(blockId);
      if (!block || block.objectType !== 'architecture-block') return;
      const connector = get().connectors.get(connectorId);
      if (!connector) return;

      get().pushHistory();

      // The connection schema's template already carries any service-specific defaults
      const entryToAdd = newEntry;

      set((state) => {
        // Update block config: read existing array at configPath, append newEntry
        const currentBlock = state.canvasObjects.get(blockId) as ArchitectureBlock;
        const existingArray = (currentBlock.config[configPath as keyof ResourceConfig] as unknown as Record<string, unknown>[] | undefined) ?? [];
        const updatedArray = [...existingArray, entryToAdd];
        const updatedBlock: ArchitectureBlock = {
          ...currentBlock,
          config: { ...currentBlock.config, [configPath]: updatedArray },
        };

        const nextCanvasObjects = new Map(state.canvasObjects);
        nextCanvasObjects.set(blockId, updatedBlock);

        // Update connector connectionConfig
        const currentConnector = state.connectors.get(connectorId)!;
        const nextConnectors = new Map(state.connectors);
        nextConnectors.set(connectorId, {
          ...currentConnector,
          connectionConfig: { ...currentConnector.connectionConfig, [connectorConfigKey]: connectorConfigValue },
        });

        return { canvasObjects: nextCanvasObjects, connectors: nextConnectors };
      });
    },

    updateLinkedEntry: (
      blockId: string,
      configPath: string,
      displayKey: string,
      entryValue: string,
      fieldKey: string,
      fieldValue: unknown,
    ): void => {
      const block = get().canvasObjects.get(blockId);
      if (!block || block.objectType !== 'architecture-block') return;

      get().pushHistory();

      set((state) => {
        const currentBlock = state.canvasObjects.get(blockId) as ArchitectureBlock;
        const existingArray = (currentBlock.config[configPath as keyof ResourceConfig] as unknown as Record<string, unknown>[] | undefined) ?? [];
        const updatedArray = existingArray.map((entry) =>
          entry[displayKey] === entryValue ? { ...entry, [fieldKey]: fieldValue } : entry
        );
        const updatedBlock: ArchitectureBlock = {
          ...currentBlock,
          config: { ...currentBlock.config, [configPath]: updatedArray },
        };

        const nextCanvasObjects = new Map(state.canvasObjects);
        nextCanvasObjects.set(blockId, updatedBlock);
        return { canvasObjects: nextCanvasObjects };
      });
    },

    removeLinkedEntry: (
      blockId: string,
      configPath: string,
      displayKey: string,
      removedValue: string,
      connectorConfigKey: string,
    ): void => {
      const block = get().canvasObjects.get(blockId);
      if (!block || block.objectType !== 'architecture-block') return;

      get().pushHistory();

      set((state) => {
        // Remove the entry from the block's config array
        const currentBlock = state.canvasObjects.get(blockId) as ArchitectureBlock;
        const existingArray = (currentBlock.config[configPath as keyof ResourceConfig] as unknown as Record<string, unknown>[] | undefined) ?? [];
        const updatedArray = existingArray.filter(
          (entry) => entry[displayKey] !== removedValue
        );
        const updatedBlock: ArchitectureBlock = {
          ...currentBlock,
          config: { ...currentBlock.config, [configPath]: updatedArray },
        };

        const nextCanvasObjects = new Map(state.canvasObjects);
        nextCanvasObjects.set(blockId, updatedBlock);

        // Clear stale connector references: find all connectors where sourceId or targetId
        // matches the block and their connectionConfig has the removed value
        const nextConnectors = new Map(state.connectors);
        for (const [connId, connector] of state.connectors) {
          if (connector.sourceId === blockId || connector.targetId === blockId) {
            const configValue = connector.connectionConfig?.[connectorConfigKey];
            if (configValue === removedValue) {
              nextConnectors.set(connId, {
                ...connector,
                connectionConfig: { ...connector.connectionConfig, [connectorConfigKey]: '' },
              });
            }
          }
        }

        return { canvasObjects: nextCanvasObjects, connectors: nextConnectors };
      });
    },
});
