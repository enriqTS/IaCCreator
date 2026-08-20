/**
 * Connectors and line anchoring — the wiring between architecture blocks.
 */

import type { StateCreator } from 'zustand';
import type { AnchorRef, ArchitectureBlock, Connector, LineObject, Point, ResourceConfig } from '@/types/diagram';
import { computeOptimalExitSide, getAnchorPoints } from '@/utils/anchor';
import type { AnchorPosition } from '@/utils/anchor';
import { getConnectionBounds } from '@/utils/bounds-utils';
import { v4 as uuidv4 } from 'uuid';
import type { DiagramStore } from './store-types';

export interface ConnectorSlice {
  // Anchor management
  updateLineAnchors: (lineId: string, anchors: { sourceAnchor?: AnchorRef | null; targetAnchor?: AnchorRef | null }) => void;
  recomputeAnchoredEndpoints: (movedObjectId: string) => void;

  // Waypoint and anchor position management
  updateLineWaypoints: (lineId: string, waypoints: Point[] | null) => void;
  updateLineAnchorPosition: (lineId: string, endpoint: 'source' | 'target', position: AnchorPosition) => void;
  updateLineLabelOffset: (lineId: string, offset: Point | null) => void;
  updateLineCustomLabel: (lineId: string, label: string | null) => void;

  // Pull-to-connect state
  pullConnectState: { sourceObjectId: string; sourceAnchorPoint: Point; sourceAnchorPosition: AnchorPosition } | null;
  setPullConnectState: (state: { sourceObjectId: string; sourceAnchorPoint: Point; sourceAnchorPosition: AnchorPosition } | null) => void;

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
}

export const createConnectorSlice: StateCreator<DiagramStore, [], [], ConnectorSlice> = (set, get) => ({
    // --- Connector state (initialized here for use by element-less store) ---
    connectors: new Map<string, Connector>(),

    // --- Anchor management ---

    updateLineAnchors: (lineId: string, anchors: { sourceAnchor?: AnchorRef | null; targetAnchor?: AnchorRef | null }): void => {
      const existing = get().canvasObjects.get(lineId);
      if (!existing || existing.objectType !== 'line') return;
      get().pushHistory();

      const updated: LineObject = { ...existing };
      if ('sourceAnchor' in anchors) {
        updated.sourceAnchor = anchors.sourceAnchor ?? null;
      }
      if ('targetAnchor' in anchors) {
        updated.targetAnchor = anchors.targetAnchor ?? null;
      }

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(lineId, updated);
        return { canvasObjects: next };
      });
    },

    recomputeAnchoredEndpoints: (movedObjectId: string): void => {
      const { canvasObjects } = get();
      const movedObj = canvasObjects.get(movedObjectId);
      if (!movedObj) return;

      const movedBounds = getConnectionBounds(movedObj);
      const updates = new Map<string, LineObject>();

      for (const obj of canvasObjects.values()) {
        if (obj.objectType !== 'line') continue;
        const line = obj as LineObject;
        const updatedLine = { ...line };
        let updated = false;

        // Re-evaluate source anchor position if the moved object is the source
        if (line.sourceAnchor?.objectId === movedObjectId) {
          // Use the center of the other object (or the free endpoint) as reference
          let otherPt = line.end;
          if (line.targetAnchor) {
            const targetObj = canvasObjects.get(line.targetAnchor.objectId);
            if (targetObj) {
              const tb = getConnectionBounds(targetObj);
              otherPt = { x: tb.x + tb.width / 2, y: tb.y + tb.height / 2 };
            }
          }
          const bestPos = computeOptimalExitSide(movedBounds, otherPt, line.sourceAnchor.anchorPosition);
          updatedLine.sourceAnchor = { ...line.sourceAnchor, anchorPosition: bestPos };
          updatedLine.start = getAnchorPoints(movedBounds)[bestPos];
          updated = true;
        }

        // Re-evaluate target anchor position if the moved object is the target
        if (line.targetAnchor?.objectId === movedObjectId) {
          // Use the center of the other object (or the free endpoint) as reference
          let otherPt = updatedLine.start;
          if (line.sourceAnchor) {
            const sourceObj = canvasObjects.get(line.sourceAnchor.objectId);
            if (sourceObj && line.sourceAnchor.objectId !== movedObjectId) {
              const sb = getConnectionBounds(sourceObj);
              otherPt = { x: sb.x + sb.width / 2, y: sb.y + sb.height / 2 };
            }
          }
          const bestPos = computeOptimalExitSide(movedBounds, otherPt, line.targetAnchor.anchorPosition);
          updatedLine.targetAnchor = { ...line.targetAnchor, anchorPosition: bestPos };
          updatedLine.end = getAnchorPoints(movedBounds)[bestPos];
          updated = true;
        }

        if (updated) {
          // Also re-evaluate the non-moved end's anchor since relative geometry changed
          if (updatedLine.sourceAnchor && updatedLine.sourceAnchor.objectId !== movedObjectId) {
            const sourceObj = canvasObjects.get(updatedLine.sourceAnchor.objectId);
            if (sourceObj) {
              const sourceBounds = getConnectionBounds(sourceObj);
              const movedCenter = { x: movedBounds.x + movedBounds.width / 2, y: movedBounds.y + movedBounds.height / 2 };
              const bestSourcePos = computeOptimalExitSide(sourceBounds, movedCenter, updatedLine.sourceAnchor.anchorPosition);
              updatedLine.sourceAnchor = { ...updatedLine.sourceAnchor, anchorPosition: bestSourcePos };
              updatedLine.start = getAnchorPoints(sourceBounds)[bestSourcePos];
            }
          }
          if (updatedLine.targetAnchor && updatedLine.targetAnchor.objectId !== movedObjectId) {
            const targetObj = canvasObjects.get(updatedLine.targetAnchor.objectId);
            if (targetObj) {
              const targetBounds = getConnectionBounds(targetObj);
              const movedCenter = { x: movedBounds.x + movedBounds.width / 2, y: movedBounds.y + movedBounds.height / 2 };
              const bestTargetPos = computeOptimalExitSide(targetBounds, movedCenter, updatedLine.targetAnchor.anchorPosition);
              updatedLine.targetAnchor = { ...updatedLine.targetAnchor, anchorPosition: bestTargetPos };
              updatedLine.end = getAnchorPoints(targetBounds)[bestTargetPos];
            }
          }
          updatedLine.waypoints = null;
          updates.set(line.id, updatedLine as LineObject);
        }
      }

      if (updates.size === 0) return;

      set((state) => {
        const next = new Map(state.canvasObjects);
        for (const [id, updated] of updates) {
          next.set(id, updated);
        }
        return { canvasObjects: next };
      });
    },

    // --- Waypoint and anchor position management ---

    updateLineWaypoints: (lineId: string, waypoints: Point[] | null): void => {
      const existing = get().canvasObjects.get(lineId);
      if (!existing || existing.objectType !== 'line') return;
      get().pushHistory();

      const updated: LineObject = { ...existing, waypoints };

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(lineId, updated);
        return { canvasObjects: next };
      });
    },

    updateLineAnchorPosition: (lineId: string, endpoint: 'source' | 'target', position: AnchorPosition): void => {
      const existing = get().canvasObjects.get(lineId);
      if (!existing || existing.objectType !== 'line') return;

      const anchorKey = endpoint === 'source' ? 'sourceAnchor' : 'targetAnchor';
      const currentAnchor = existing[anchorKey];
      if (!currentAnchor) return; // No anchor to update

      const updated: LineObject = {
        ...existing,
        [anchorKey]: { ...currentAnchor, anchorPosition: position },
      };

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(lineId, updated);
        return { canvasObjects: next };
      });
    },

    updateLineLabelOffset: (lineId: string, offset: Point | null): void => {
      const existing = get().canvasObjects.get(lineId);
      if (!existing || existing.objectType !== 'line') return;

      const updated: LineObject = { ...existing, labelOffset: offset };
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(lineId, updated);
        return { canvasObjects: next };
      });
    },

    updateLineCustomLabel: (lineId: string, label: string | null): void => {
      const existing = get().canvasObjects.get(lineId);
      if (!existing || existing.objectType !== 'line') return;
      get().pushHistory();

      const updated: LineObject = { ...existing, customLabel: label };
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(lineId, updated);
        return { canvasObjects: next };
      });
    },

    // --- Pull-to-connect state ---

    pullConnectState: null as { sourceObjectId: string; sourceAnchorPoint: Point; sourceAnchorPosition: AnchorPosition } | null,

    setPullConnectState: (state: { sourceObjectId: string; sourceAnchorPoint: Point; sourceAnchorPosition: AnchorPosition } | null): void => {
      set({ pullConnectState: state });
    },

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
