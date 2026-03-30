import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type {
  ServiceType,
  Point,
  DiagramElement,
  Connector,
  ResourceConfig,
  Viewport,
  Tool,
  EnvironmentConfig,
  CanvasObject,
  CanvasObjectCreationPayload,
  ArchitectureBlock,
  LineObject,
  GeometricObject,
  TextObject,
  UMLObject,
  GeometricShape,
  UMLKind,
  ArchitectureBlockVisualConfig,
  LineVisualConfig,
  GeometricVisualConfig,
  TextVisualConfig,
  UMLVisualConfig,
  Rect,
  ObjectGroup,
  AnchorRef,
  RoutingMode,
} from '@/types/diagram';
import {
  MIN_OBJECT_WIDTH,
  MIN_OBJECT_HEIGHT,
  DEFAULT_BLOCK_VISUAL,
  DEFAULT_LINE_VISUAL,
  DEFAULT_GEO_VISUAL,
  DEFAULT_TEXT_VISUAL,
  DEFAULT_UML_VISUAL,
  DEFAULT_UML_CLASS_DATA,
  getObjectBounds,
} from '@/types/diagram';
import type { DiagramState, ArchitectureDescription, SerializedCanvasObject } from '@/types/serialization';
import { CURRENT_DIAGRAM_VERSION } from '@/types/serialization';
import type { DiagramSummary } from '@/types/api';
import { zoomAtPoint } from '@/utils/viewport';
import { getAnchorPoints, findNearestAnchorPosition } from '@/utils/anchor';
import type { AnchorPosition } from '@/utils/anchor';
import { apiClient } from '@/utils/api-client';
import { useToastStore } from '@/store/toast-store';
import type { GlobalTerraformConfig } from '@/types/terraform-variables';
import { getDefaultVariables, DEFAULT_GLOBAL_CONFIG } from '@/types/terraform-variables';

import { MIN_PANEL_HEIGHT, MAX_PANEL_HEIGHT_RATIO, DEFAULT_PANEL_HEIGHT, MIN_SIDEBAR_WIDTH, MAX_SIDEBAR_WIDTH_RATIO, DEFAULT_SIDEBAR_WIDTH } from '@/components/config/panel-constants';

interface HistoryEntry {
  elements: Map<string, DiagramElement>;
  connectors: Map<string, Connector>;
  canvasObjects: Map<string, CanvasObject>;
  objectGroups: Map<string, ObjectGroup>;
}

const MAX_HISTORY = 50;

/** Deep-clone a Map of diagram objects */
function cloneMap<K, V>(map: Map<K, V>): Map<K, V> {
  const result = new Map<K, V>();
  for (const [k, v] of map) {
    result.set(k, { ...(v as object) } as V);
  }
  return result;
}

function takeSnapshot(state: {
  elements: Map<string, DiagramElement>;
  connectors: Map<string, Connector>;
  canvasObjects?: Map<string, CanvasObject>;
  objectGroups?: Map<string, ObjectGroup>;
}): HistoryEntry {
  return {
    elements: cloneMap(state.elements),
    connectors: cloneMap(state.connectors),
    canvasObjects: cloneMap(state.canvasObjects ?? new Map()),
    objectGroups: cloneMap(state.objectGroups ?? new Map()),
  };
}

export interface DiagramStore {
  // Element state
  elements: Map<string, DiagramElement>;
  addElement: (serviceType: ServiceType, position: Point) => string;
  updateElementPosition: (id: string, position: Point) => void;
  updateElementConfig: (id: string, config: Partial<ResourceConfig>) => void;
  updateElementName: (id: string, name: string) => void;
  removeElement: (id: string) => void;

  // Canvas object state
  canvasObjects: Map<string, CanvasObject>;
  selectedObjectIds: Set<string>;
  addCanvasObject: (obj: CanvasObjectCreationPayload) => string;
  updateCanvasObject: (id: string, updates: Partial<CanvasObject>) => void;
  removeCanvasObject: (id: string) => void;
  selectObject: (id: string | null) => void;
  toggleObjectSelection: (id: string) => void;
  selectObjectsByRect: (rect: Rect) => void;
  clearSelection: () => void;
  updateVisualConfig: (id: string, config: Partial<ArchitectureBlockVisualConfig | LineVisualConfig | GeometricVisualConfig | TextVisualConfig | UMLVisualConfig>) => void;
  updateObjectBounds: (id: string, bounds: { width?: number; height?: number }) => void;
  updateLineEndpoint: (id: string, endpoint: 'start' | 'end', position: Point) => void;

  // Z-order actions
  bringToFront: (id: string) => void;
  sendToBack: (id: string) => void;
  bringForward: (id: string) => void;
  sendBackward: (id: string) => void;

  // Grouping
  objectGroups: Map<string, ObjectGroup>;
  groupSelectedObjects: () => string | null;
  ungroupObjects: (groupId: string) => void;

  // Clipboard
  clipboard: CanvasObject[];
  copySelectedObjects: () => void;
  pasteObjects: (position: Point) => void;

  // Duplicate
  duplicateSelectedObjects: () => void;

  // Lock
  toggleLockObjects: (ids: Set<string>) => void;

  // Select all
  selectAllObjects: () => void;

  // Fit to screen
  fitToScreen: (containerRect: { width: number; height: number }) => void;

  // Multi-object move
  moveSelectedObjects: (dx: number, dy: number) => void;

  // Text editing
  editingTextId: string | null;
  setEditingTextId: (id: string | null) => void;
  updateTextContent: (id: string, content: string) => void;

  // Anchor management
  updateLineAnchors: (lineId: string, anchors: { sourceAnchor?: AnchorRef | null; targetAnchor?: AnchorRef | null }) => void;
  recomputeAnchoredEndpoints: (movedObjectId: string) => void;

  // Waypoint and anchor position management
  updateLineWaypoints: (lineId: string, waypoints: Point[] | null) => void;
  updateLineAnchorPosition: (lineId: string, endpoint: 'source' | 'target', position: AnchorPosition) => void;

  // Pull-to-connect state
  pullConnectState: { sourceObjectId: string; sourceAnchorPoint: Point; sourceAnchorPosition: AnchorPosition } | null;
  setPullConnectState: (state: { sourceObjectId: string; sourceAnchorPoint: Point; sourceAnchorPosition: AnchorPosition } | null) => void;

  // Connector state
  connectors: Map<string, Connector>;
  addConnector: (sourceId: string, targetId: string, connectionType?: string) => string;
  updateConnectorType: (id: string, connectionType: string) => void;
  removeConnector: (id: string) => void;

  // Viewport state
  viewport: Viewport;
  pan: (dx: number, dy: number) => void;
  zoom: (factor: number, center: Point) => void;

  // UI state
  activeTool: Tool;
  setActiveTool: (tool: Tool) => void;
  selectedElementId: string | null;
  selectedConnectorId: string | null;
  selectElement: (id: string | null) => void;
  selectConnector: (id: string | null) => void;
  pendingConnectorSourceId: string | null;

  // History (undo/redo)
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  beginDragGesture: () => void;

  // Project state
  projectName: string;
  environments: EnvironmentConfig[];
  setProjectName: (name: string) => void;
  setEnvironments: (envs: EnvironmentConfig[]) => void;

  // Terraform variables
  setTerraformVariable: (objectId: string, varName: string, value: string | number | boolean) => void;
  setTerraformVariables: (objectId: string, vars: Record<string, string | number | boolean>) => void;
  globalTerraformConfig: GlobalTerraformConfig;
  updateGlobalTerraformConfig: (updates: Partial<GlobalTerraformConfig>) => void;

  // Serialization
  serializeDiagramState: () => DiagramState;
  loadDiagramState: (state: DiagramState) => void;
  serializeToArchitectureDescription: () => ArchitectureDescription;

  // Server persistence
  currentDiagramId: string | null;
  diagramSummaries: DiagramSummary[];
  isSaving: boolean;
  isLoading: boolean;
  saveDiagramToServer: () => Promise<void>;
  updateDiagramOnServer: (id: string) => Promise<void>;
  loadDiagramFromServer: (id: string) => Promise<void>;
  listDiagramsFromServer: () => Promise<DiagramSummary[]>;
  deleteDiagramFromServer: (id: string) => Promise<void>;

  // Bottom panel state
  bottomPanelExpanded: boolean;
  bottomPanelHeight: number;
  setBottomPanelExpanded: (expanded: boolean) => void;
  setBottomPanelHeight: (height: number) => void;
  toggleBottomPanel: () => void;

  // Sidebar panel state
  sidebarExpanded: boolean;
  sidebarWidth: number;
  setSidebarExpanded: (expanded: boolean) => void;
  setSidebarWidth: (width: number) => void;
  toggleSidebar: () => void;

  // Global routing mode
  globalRoutingMode: RoutingMode;
  setGlobalRoutingMode: (mode: RoutingMode) => void;

  /** @internal — exposed for testing reset only */
  _undoStack: HistoryEntry[];
  _redoStack: HistoryEntry[];
}

export const useDiagramStore = create<DiagramStore>((set, get) => {
  function pushHistory() {
    const { elements, connectors, canvasObjects, objectGroups, _undoStack } = get();
    const snapshot = takeSnapshot({ elements, connectors, canvasObjects, objectGroups });
    let newStack = [..._undoStack, snapshot];
    if (newStack.length > MAX_HISTORY) {
      newStack = newStack.slice(newStack.length - MAX_HISTORY);
    }
    set({ _undoStack: newStack, _redoStack: [], canUndo: true, canRedo: false });
  }

  return {
    // --- Element state ---
    elements: new Map<string, DiagramElement>(),
    connectors: new Map<string, Connector>(),

    addElement: (serviceType: ServiceType, position: Point): string => {
      pushHistory();

      const id = uuidv4();
      const { elements } = get();

      let count = 0;
      for (const el of elements.values()) {
        if (el.serviceType === serviceType) count++;
      }
      const name = `${serviceType}-${count + 1}`;

      const element: DiagramElement = {
        id,
        serviceType,
        name,
        position,
        config: {},
      };

      set((state) => {
        const next = new Map(state.elements);
        next.set(id, element);
        return { elements: next };
      });

      return id;
    },

    updateElementPosition: (id: string, position: Point): void => {
      const el = get().elements.get(id);
      if (!el) return;
      pushHistory();
      set((state) => {
        const next = new Map(state.elements);
        next.set(id, { ...state.elements.get(id)!, position });
        return { elements: next };
      });
    },

    updateElementConfig: (id: string, config: Partial<ResourceConfig>): void => {
      const el = get().elements.get(id);
      if (!el) return;
      pushHistory();
      set((state) => {
        const current = state.elements.get(id)!;
        const next = new Map(state.elements);
        next.set(id, { ...current, config: { ...current.config, ...config } });
        return { elements: next };
      });
    },

    updateElementName: (id: string, name: string): void => {
      const el = get().elements.get(id);
      if (!el) return;
      pushHistory();
      set((state) => {
        const next = new Map(state.elements);
        next.set(id, { ...state.elements.get(id)!, name });
        return { elements: next };
      });
    },

    removeElement: (id: string): void => {
      if (!get().elements.has(id)) return;
      pushHistory();
      set((state) => {
        const nextElements = new Map(state.elements);
        nextElements.delete(id);

        const nextConnectors = new Map(state.connectors);
        for (const [cid, conn] of state.connectors) {
          if (conn.sourceId === id || conn.targetId === id) {
            nextConnectors.delete(cid);
          }
        }

        return { elements: nextElements, connectors: nextConnectors };
      });
    },

    // --- Canvas object state ---
    canvasObjects: new Map<string, CanvasObject>(),
    selectedObjectIds: new Set<string>(),
    objectGroups: new Map<string, ObjectGroup>(),
    clipboard: [] as CanvasObject[],

    addCanvasObject: (obj: CanvasObjectCreationPayload): string => {
      pushHistory();
      const id = uuidv4();
      // Assign zIndex as maxZIndex + 1
      const { canvasObjects } = get();
      let maxZ = -1;
      for (const existing of canvasObjects.values()) {
        if (existing.zIndex > maxZ) maxZ = existing.zIndex;
      }
      let canvasObject = { ...obj, id, zIndex: maxZ + 1 } as CanvasObject;

      // Initialize terraformVariables for architecture blocks
      if (canvasObject.objectType === 'architecture-block') {
        canvasObject = {
          ...canvasObject,
          terraformVariables: {
            ...getDefaultVariables(canvasObject.serviceType),
            ...(obj as { terraformVariables?: Record<string, string | number | boolean> }).terraformVariables,
          },
        };
      }

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, canvasObject);
        return { canvasObjects: next };
      });

      return id;
    },

    updateCanvasObject: (id: string, updates: Partial<CanvasObject>): void => {
      const existing = get().canvasObjects.get(id);
      if (!existing) return;

      const merged = { ...existing, ...updates, id: existing.id, objectType: existing.objectType } as CanvasObject;

      // Enforce minimum dimension clamping for objects with width/height
      if (merged.objectType === 'architecture-block') {
        merged.visualConfig = {
          ...merged.visualConfig,
          width: Math.max(merged.visualConfig.width, MIN_OBJECT_WIDTH),
          height: Math.max(merged.visualConfig.height, MIN_OBJECT_HEIGHT),
        };
      } else if (merged.objectType === 'geometric') {
        merged.visualConfig = {
          ...merged.visualConfig,
          width: Math.max(merged.visualConfig.width, MIN_OBJECT_WIDTH),
          height: Math.max(merged.visualConfig.height, MIN_OBJECT_HEIGHT),
        };
      }

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, merged);
        return { canvasObjects: next };
      });
    },

    removeCanvasObject: (id: string): void => {
      if (!get().canvasObjects.has(id)) return;
      pushHistory();

      set((state) => {
        const next = new Map(state.canvasObjects);
        const obj = state.canvasObjects.get(id)!;
        next.delete(id);

        // Cascade-delete connectors for architecture blocks
        let nextConnectors = state.connectors;
        if (obj.objectType === 'architecture-block') {
          nextConnectors = new Map(state.connectors);
          for (const [cid, conn] of state.connectors) {
            if (conn.sourceId === id || conn.targetId === id) {
              nextConnectors.delete(cid);
            }
          }
        }

        // Clear selection if deleting the selected object
        const nextSelectedObjectIds = new Set(state.selectedObjectIds);
        nextSelectedObjectIds.delete(id);

        // Handle group membership: remove from group, auto-dissolve if < 2 members
        const nextGroups = new Map(state.objectGroups);
        if (obj.groupId) {
          const group = nextGroups.get(obj.groupId);
          if (group) {
            const updatedMembers = group.memberIds.filter((mid) => mid !== id);
            if (updatedMembers.length < 2) {
              // Auto-dissolve: clear groupId on remaining members
              for (const memberId of updatedMembers) {
                const member = next.get(memberId);
                if (member) {
                  next.set(memberId, { ...member, groupId: undefined } as CanvasObject);
                }
              }
              nextGroups.delete(obj.groupId);
            } else {
              nextGroups.set(obj.groupId, { ...group, memberIds: updatedMembers });
            }
          }
        }

        // Detach anchors on lines referencing the deleted object (nullify, don't delete lines)
        for (const [lineId, lineObj] of next) {
          if (lineObj.objectType !== 'line') continue;
          const line = lineObj as LineObject;
          let needsUpdate = false;
          let newSourceAnchor = line.sourceAnchor;
          let newTargetAnchor = line.targetAnchor;

          if (line.sourceAnchor?.objectId === id) {
            newSourceAnchor = null;
            needsUpdate = true;
          }
          if (line.targetAnchor?.objectId === id) {
            newTargetAnchor = null;
            needsUpdate = true;
          }
          if (needsUpdate) {
            next.set(lineId, { ...line, sourceAnchor: newSourceAnchor, targetAnchor: newTargetAnchor });
          }
        }

        return { canvasObjects: next, connectors: nextConnectors, selectedObjectIds: nextSelectedObjectIds, objectGroups: nextGroups };
      });
    },

    selectObject: (id: string | null): void => {
      if (!id) {
        set({ selectedObjectIds: new Set() });
        return;
      }
      const { canvasObjects, objectGroups } = get();
      const obj = canvasObjects.get(id);
      if (obj?.groupId) {
        const group = objectGroups.get(obj.groupId);
        if (group) {
          set({ selectedObjectIds: new Set(group.memberIds) });
          return;
        }
      }
      set({ selectedObjectIds: new Set([id]) });
    },

    toggleObjectSelection: (id: string): void => {
      set((state) => {
        const next = new Set(state.selectedObjectIds);
        if (next.has(id)) {
          next.delete(id);
        } else {
          next.add(id);
        }
        return { selectedObjectIds: next };
      });
    },

    selectObjectsByRect: (rect: Rect): void => {
      const { canvasObjects } = get();
      const selected = new Set<string>();
      for (const obj of canvasObjects.values()) {
        const bounds = getObjectBounds(obj);
        // Check AABB intersection
        if (
          bounds.x + bounds.width > rect.x &&
          bounds.x < rect.x + rect.width &&
          bounds.y + bounds.height > rect.y &&
          bounds.y < rect.y + rect.height
        ) {
          selected.add(obj.id);
        }
      }
      set({ selectedObjectIds: selected });
    },

    clearSelection: (): void => {
      set({ selectedObjectIds: new Set() });
    },

    updateVisualConfig: (id: string, config: Partial<ArchitectureBlockVisualConfig | LineVisualConfig | GeometricVisualConfig | TextVisualConfig | UMLVisualConfig>): void => {
      const existing = get().canvasObjects.get(id);
      if (!existing) return;
      pushHistory();

      const mergedConfig = { ...existing.visualConfig, ...config };

      // Enforce minimum dimensions for object types with width/height
      if (existing.objectType === 'architecture-block' || existing.objectType === 'geometric' || existing.objectType === 'text' || existing.objectType === 'uml') {
        const withDims = mergedConfig as { width: number; height: number };
        withDims.width = Math.max(withDims.width, MIN_OBJECT_WIDTH);
        withDims.height = Math.max(withDims.height, MIN_OBJECT_HEIGHT);
      }

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...existing, visualConfig: mergedConfig } as CanvasObject);
        return { canvasObjects: next };
      });
    },

    updateObjectBounds: (id: string, bounds: { width?: number; height?: number }): void => {
      const existing = get().canvasObjects.get(id);
      if (!existing) return;
      if (existing.objectType === 'line') return; // Lines don't have width/height bounds

      const currentConfig = existing.visualConfig as { width: number; height: number };
      const newWidth = Math.max(bounds.width ?? currentConfig.width, MIN_OBJECT_WIDTH);
      const newHeight = Math.max(bounds.height ?? currentConfig.height, MIN_OBJECT_HEIGHT);

      const mergedConfig = { ...existing.visualConfig, width: newWidth, height: newHeight };

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...existing, visualConfig: mergedConfig } as CanvasObject);
        return { canvasObjects: next };
      });
    },

    updateLineEndpoint: (id: string, endpoint: 'start' | 'end', position: Point): void => {
      const existing = get().canvasObjects.get(id);
      if (!existing || existing.objectType !== 'line') return;

      const updated = { ...existing, [endpoint]: { ...position }, waypoints: null };

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, updated);
        return { canvasObjects: next };
      });
    },

    // --- Z-order actions ---

    bringToFront: (id: string): void => {
      const { canvasObjects } = get();
      const target = canvasObjects.get(id);
      if (!target) return;

      let maxZ = -Infinity;
      for (const obj of canvasObjects.values()) {
        if (obj.id !== id && obj.zIndex > maxZ) maxZ = obj.zIndex;
      }
      // If already on top (or only object), no-op
      if (canvasObjects.size <= 1 || target.zIndex > maxZ) return;

      const newZ = maxZ + 1;
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...target, zIndex: newZ } as CanvasObject);
        return { canvasObjects: next };
      });
    },

    sendToBack: (id: string): void => {
      const { canvasObjects } = get();
      const target = canvasObjects.get(id);
      if (!target) return;

      let minZ = Infinity;
      for (const obj of canvasObjects.values()) {
        if (obj.id !== id && obj.zIndex < minZ) minZ = obj.zIndex;
      }
      // If already at back (or only object), no-op
      if (canvasObjects.size <= 1 || target.zIndex < minZ) return;

      const newZ = minZ - 1;
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...target, zIndex: newZ } as CanvasObject);
        return { canvasObjects: next };
      });
    },

    bringForward: (id: string): void => {
      const { canvasObjects } = get();
      const target = canvasObjects.get(id);
      if (!target) return;

      // Find the object directly above (smallest zIndex greater than target's)
      let aboveObj: CanvasObject | null = null;
      for (const obj of canvasObjects.values()) {
        if (obj.id !== id && obj.zIndex > target.zIndex) {
          if (!aboveObj || obj.zIndex < aboveObj.zIndex) {
            aboveObj = obj;
          }
        }
      }
      if (!aboveObj) return; // Already on top

      // Swap zIndex values
      const targetNewZ = aboveObj.zIndex;
      const aboveNewZ = target.zIndex;
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...target, zIndex: targetNewZ } as CanvasObject);
        next.set(aboveObj!.id, { ...aboveObj!, zIndex: aboveNewZ } as CanvasObject);
        return { canvasObjects: next };
      });
    },

    sendBackward: (id: string): void => {
      const { canvasObjects } = get();
      const target = canvasObjects.get(id);
      if (!target) return;

      // Find the object directly below (largest zIndex less than target's)
      let belowObj: CanvasObject | null = null;
      for (const obj of canvasObjects.values()) {
        if (obj.id !== id && obj.zIndex < target.zIndex) {
          if (!belowObj || obj.zIndex > belowObj.zIndex) {
            belowObj = obj;
          }
        }
      }
      if (!belowObj) return; // Already at back

      // Swap zIndex values
      const targetNewZ = belowObj.zIndex;
      const belowNewZ = target.zIndex;
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...target, zIndex: targetNewZ } as CanvasObject);
        next.set(belowObj!.id, { ...belowObj!, zIndex: belowNewZ } as CanvasObject);
        return { canvasObjects: next };
      });
    },

    // --- Grouping actions ---

    groupSelectedObjects: (): string | null => {
      const { selectedObjectIds, canvasObjects, objectGroups } = get();
      // Require at least 2 selected objects
      if (selectedObjectIds.size < 2) return null;

      // Verify all selected IDs exist
      for (const id of selectedObjectIds) {
        if (!canvasObjects.has(id)) return null;
      }

      pushHistory();

      const groupId = uuidv4();
      // Auto-generate group name
      const groupNumber = objectGroups.size + 1;
      const groupName = `Group ${groupNumber}`;
      const memberIds = Array.from(selectedObjectIds);

      set((state) => {
        const nextObjects = new Map(state.canvasObjects);
        const nextGroups = new Map(state.objectGroups);

        // Remove members from any existing groups first
        for (const memberId of memberIds) {
          const obj = nextObjects.get(memberId);
          if (obj && obj.groupId) {
            const oldGroup = nextGroups.get(obj.groupId);
            if (oldGroup) {
              const remaining = oldGroup.memberIds.filter((mid) => mid !== memberId);
              if (remaining.length < 2) {
                // Auto-dissolve old group
                for (const rid of remaining) {
                  const rObj = nextObjects.get(rid);
                  if (rObj) {
                    nextObjects.set(rid, { ...rObj, groupId: undefined } as CanvasObject);
                  }
                }
                nextGroups.delete(obj.groupId);
              } else {
                nextGroups.set(obj.groupId, { ...oldGroup, memberIds: remaining });
              }
            }
          }
        }

        // Set groupId on all members
        for (const memberId of memberIds) {
          const obj = nextObjects.get(memberId);
          if (obj) {
            nextObjects.set(memberId, { ...obj, groupId: groupId } as CanvasObject);
          }
        }

        // Create the new group
        const newGroup: ObjectGroup = { id: groupId, name: groupName, memberIds };
        nextGroups.set(groupId, newGroup);

        return { canvasObjects: nextObjects, objectGroups: nextGroups };
      });

      return groupId;
    },

    ungroupObjects: (groupId: string): void => {
      const { objectGroups } = get();
      const group = objectGroups.get(groupId);
      if (!group) return;
      pushHistory();

      set((state) => {
        const nextObjects = new Map(state.canvasObjects);
        const nextGroups = new Map(state.objectGroups);

        // Clear groupId on all members
        for (const memberId of group.memberIds) {
          const obj = nextObjects.get(memberId);
          if (obj) {
            nextObjects.set(memberId, { ...obj, groupId: undefined } as CanvasObject);
          }
        }

        // Remove the group
        nextGroups.delete(groupId);

        return { canvasObjects: nextObjects, objectGroups: nextGroups };
      });
    },

    // --- Clipboard actions ---

    copySelectedObjects: (): void => {
      const { selectedObjectIds, canvasObjects } = get();
      if (selectedObjectIds.size === 0) return;

      const copied: CanvasObject[] = [];
      for (const id of selectedObjectIds) {
        const obj = canvasObjects.get(id);
        if (obj) {
          copied.push({ ...obj });
        }
      }
      set({ clipboard: copied });
    },

    pasteObjects: (position: Point): void => {
      const { clipboard, canvasObjects } = get();
      if (clipboard.length === 0) return;

      pushHistory();

      // Compute centroid of copied objects
      let sumX = 0;
      let sumY = 0;
      for (const obj of clipboard) {
        if (obj.objectType === 'line') {
          sumX += (obj.start.x + obj.end.x) / 2;
          sumY += (obj.start.y + obj.end.y) / 2;
        } else {
          sumX += obj.position.x;
          sumY += obj.position.y;
        }
      }
      const centroidX = sumX / clipboard.length;
      const centroidY = sumY / clipboard.length;

      // Compute max zIndex
      let maxZ = -1;
      for (const existing of canvasObjects.values()) {
        if (existing.zIndex > maxZ) maxZ = existing.zIndex;
      }

      const newIds = new Set<string>();
      const nextObjects = new Map(canvasObjects);

      for (const obj of clipboard) {
        const newId = uuidv4();
        newIds.add(newId);
        maxZ++;

        if (obj.objectType === 'line') {
          const offsetX = position.x - centroidX;
          const offsetY = position.y - centroidY;
          const pasted: LineObject = {
            ...obj,
            id: newId,
            zIndex: maxZ,
            groupId: undefined,
            start: { x: obj.start.x + offsetX, y: obj.start.y + offsetY },
            end: { x: obj.end.x + offsetX, y: obj.end.y + offsetY },
          };
          nextObjects.set(newId, pasted);
        } else if (obj.objectType === 'architecture-block') {
          const offsetX = position.x - centroidX;
          const offsetY = position.y - centroidY;
          const pasted: ArchitectureBlock = {
            ...obj,
            id: newId,
            zIndex: maxZ,
            groupId: undefined,
            position: { x: obj.position.x + offsetX, y: obj.position.y + offsetY },
          };
          nextObjects.set(newId, pasted);
        } else {
          // geometric
          const offsetX = position.x - centroidX;
          const offsetY = position.y - centroidY;
          const pasted: GeometricObject = {
            ...obj,
            id: newId,
            zIndex: maxZ,
            groupId: undefined,
            position: { x: obj.position.x + offsetX, y: obj.position.y + offsetY },
          };
          nextObjects.set(newId, pasted);
        }
      }

      set({ canvasObjects: nextObjects, selectedObjectIds: newIds });
    },

    // --- Duplicate ---

    duplicateSelectedObjects: (): void => {
      const { selectedObjectIds, canvasObjects } = get();
      if (selectedObjectIds.size === 0) return;

      pushHistory();

      let maxZ = -1;
      for (const existing of canvasObjects.values()) {
        if (existing.zIndex > maxZ) maxZ = existing.zIndex;
      }

      const newIds = new Set<string>();
      const nextObjects = new Map(canvasObjects);

      for (const id of selectedObjectIds) {
        const obj = canvasObjects.get(id);
        if (!obj) continue;

        const newId = uuidv4();
        newIds.add(newId);
        maxZ++;

        if (obj.objectType === 'line') {
          const dup: LineObject = {
            ...obj,
            id: newId,
            zIndex: maxZ,
            groupId: undefined,
            start: { x: obj.start.x + 20, y: obj.start.y + 20 },
            end: { x: obj.end.x + 20, y: obj.end.y + 20 },
          };
          nextObjects.set(newId, dup);
        } else if (obj.objectType === 'architecture-block') {
          const dup: ArchitectureBlock = {
            ...obj,
            id: newId,
            zIndex: maxZ,
            groupId: undefined,
            position: { x: obj.position.x + 20, y: obj.position.y + 20 },
          };
          nextObjects.set(newId, dup);
        } else {
          // geometric
          const dup: GeometricObject = {
            ...obj,
            id: newId,
            zIndex: maxZ,
            groupId: undefined,
            position: { x: obj.position.x + 20, y: obj.position.y + 20 },
          };
          nextObjects.set(newId, dup);
        }
      }

      set({ canvasObjects: nextObjects, selectedObjectIds: newIds });
    },

    // --- Lock/Unlock ---

    toggleLockObjects: (ids: Set<string>): void => {
      const { canvasObjects } = get();
      if (ids.size === 0) return;

      // Determine if any are unlocked
      let anyUnlocked = false;
      for (const id of ids) {
        const obj = canvasObjects.get(id);
        if (obj && !obj.locked) {
          anyUnlocked = true;
          break;
        }
      }

      pushHistory();

      const newLocked = anyUnlocked; // if any unlocked, lock all; if all locked, unlock all

      set((state) => {
        const next = new Map(state.canvasObjects);
        for (const id of ids) {
          const obj = next.get(id);
          if (obj) {
            next.set(id, { ...obj, locked: newLocked } as CanvasObject);
          }
        }
        return { canvasObjects: next };
      });
    },

    // --- Select all ---

    selectAllObjects: (): void => {
      const { canvasObjects } = get();
      if (canvasObjects.size === 0) return;
      const allIds = new Set<string>(canvasObjects.keys());
      set({ selectedObjectIds: allIds });
    },

    // --- Fit to screen ---

    fitToScreen: (containerRect: { width: number; height: number }): void => {
      const { canvasObjects } = get();
      if (canvasObjects.size === 0) return;

      const PADDING = 40;

      // Compute bounding box of all objects
      let minX = Infinity;
      let minY = Infinity;
      let maxX = -Infinity;
      let maxY = -Infinity;

      for (const obj of canvasObjects.values()) {
        const bounds = getObjectBounds(obj);
        minX = Math.min(minX, bounds.x);
        minY = Math.min(minY, bounds.y);
        maxX = Math.max(maxX, bounds.x + bounds.width);
        maxY = Math.max(maxY, bounds.y + bounds.height);
      }

      const contentWidth = maxX - minX;
      const contentHeight = maxY - minY;

      // Available space after padding
      const availableWidth = containerRect.width - PADDING * 2;
      const availableHeight = containerRect.height - PADDING * 2;

      if (availableWidth <= 0 || availableHeight <= 0) return;

      // Calculate scale to fit
      let scale = Math.min(
        availableWidth / contentWidth,
        availableHeight / contentHeight
      );

      // Clamp scale to 0.1-5.0
      scale = Math.max(0.1, Math.min(5.0, scale));

      // Center the content: offset so that the center of the bounding box maps to the center of the container
      const contentCenterX = (minX + maxX) / 2;
      const contentCenterY = (minY + maxY) / 2;

      const offsetX = containerRect.width / 2 - contentCenterX * scale;
      const offsetY = containerRect.height / 2 - contentCenterY * scale;

      set({
        viewport: { offsetX, offsetY, scale },
      });
    },

    // --- Multi-object move ---

    moveSelectedObjects: (dx: number, dy: number): void => {
      const { selectedObjectIds, canvasObjects, objectGroups } = get();
      if (selectedObjectIds.size === 0) return;

      // Expand selection to include all group members for any selected grouped object
      const idsToMove = new Set<string>(selectedObjectIds);
      for (const id of selectedObjectIds) {
        const obj = canvasObjects.get(id);
        if (obj?.groupId) {
          const group = objectGroups.get(obj.groupId);
          if (group) {
            for (const memberId of group.memberIds) {
              idsToMove.add(memberId);
            }
          }
        }
      }

      set((state) => {
        const next = new Map(state.canvasObjects);
        for (const id of idsToMove) {
          const obj = next.get(id);
          if (!obj) continue;
          if (obj.locked) continue;

          if (obj.objectType === 'line') {
            next.set(id, {
              ...obj,
              start: { x: obj.start.x + dx, y: obj.start.y + dy },
              end: { x: obj.end.x + dx, y: obj.end.y + dy },
            });
          } else {
            // architecture-block, geometric, text, uml
            next.set(id, {
              ...obj,
              position: { x: obj.position.x + dx, y: obj.position.y + dy },
            } as CanvasObject);
          }
        }
        return { canvasObjects: next };
      });

      // Recompute anchored endpoints for each moved non-line object
      for (const id of idsToMove) {
        const obj = get().canvasObjects.get(id);
        if (obj && obj.objectType !== 'line') {
          get().recomputeAnchoredEndpoints(id);
        }
      }
    },

    // --- Text editing ---
    editingTextId: null as string | null,

    setEditingTextId: (id: string | null): void => {
      set({ editingTextId: id });
    },

    updateTextContent: (id: string, content: string): void => {
      const existing = get().canvasObjects.get(id);
      if (!existing || existing.objectType !== 'text') return;

      // If content is empty or whitespace-only, auto-remove the text object
      if (!content || content.trim() === '') {
        get().removeCanvasObject(id);
        return;
      }

      pushHistory();
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...existing, content } as import('@/types/diagram').TextObject);
        return { canvasObjects: next };
      });
    },

    // --- Anchor management ---

    updateLineAnchors: (lineId: string, anchors: { sourceAnchor?: AnchorRef | null; targetAnchor?: AnchorRef | null }): void => {
      const existing = get().canvasObjects.get(lineId);
      if (!existing || existing.objectType !== 'line') return;
      pushHistory();

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

      const movedBounds = getObjectBounds(movedObj);
      const updates = new Map<string, LineObject>();

      for (const obj of canvasObjects.values()) {
        if (obj.objectType !== 'line') continue;
        const line = obj as LineObject;
        let updatedLine = { ...line };
        let updated = false;

        // Re-evaluate source anchor position if the moved object is the source
        if (line.sourceAnchor?.objectId === movedObjectId) {
          // Use the center of the other object (or the free endpoint) as reference
          let otherPt = line.end;
          if (line.targetAnchor) {
            const targetObj = canvasObjects.get(line.targetAnchor.objectId);
            if (targetObj) {
              const tb = getObjectBounds(targetObj);
              otherPt = { x: tb.x + tb.width / 2, y: tb.y + tb.height / 2 };
            }
          }
          const bestPos = findNearestAnchorPosition(otherPt, movedBounds, line.sourceAnchor.anchorPosition);
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
              const sb = getObjectBounds(sourceObj);
              otherPt = { x: sb.x + sb.width / 2, y: sb.y + sb.height / 2 };
            }
          }
          const bestPos = findNearestAnchorPosition(otherPt, movedBounds, line.targetAnchor.anchorPosition);
          updatedLine.targetAnchor = { ...line.targetAnchor, anchorPosition: bestPos };
          updatedLine.end = getAnchorPoints(movedBounds)[bestPos];
          updated = true;
        }

        if (updated) {
          // Also re-evaluate the non-moved end's anchor since relative geometry changed
          if (updatedLine.sourceAnchor && updatedLine.sourceAnchor.objectId !== movedObjectId) {
            const sourceObj = canvasObjects.get(updatedLine.sourceAnchor.objectId);
            if (sourceObj) {
              const sourceBounds = getObjectBounds(sourceObj);
              const movedCenter = { x: movedBounds.x + movedBounds.width / 2, y: movedBounds.y + movedBounds.height / 2 };
              const bestSourcePos = findNearestAnchorPosition(movedCenter, sourceBounds, updatedLine.sourceAnchor.anchorPosition);
              updatedLine.sourceAnchor = { ...updatedLine.sourceAnchor, anchorPosition: bestSourcePos };
              updatedLine.start = getAnchorPoints(sourceBounds)[bestSourcePos];
            }
          }
          if (updatedLine.targetAnchor && updatedLine.targetAnchor.objectId !== movedObjectId) {
            const targetObj = canvasObjects.get(updatedLine.targetAnchor.objectId);
            if (targetObj) {
              const targetBounds = getObjectBounds(targetObj);
              const movedCenter = { x: movedBounds.x + movedBounds.width / 2, y: movedBounds.y + movedBounds.height / 2 };
              const bestTargetPos = findNearestAnchorPosition(movedCenter, targetBounds, updatedLine.targetAnchor.anchorPosition);
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
      pushHistory();

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

    // --- Pull-to-connect state ---

    pullConnectState: null as { sourceObjectId: string; sourceAnchorPoint: Point; sourceAnchorPosition: AnchorPosition } | null,

    setPullConnectState: (state: { sourceObjectId: string; sourceAnchorPoint: Point; sourceAnchorPosition: AnchorPosition } | null): void => {
      set({ pullConnectState: state });
    },

    // --- Connector state ---

    addConnector: (sourceId: string, targetId: string, connectionType?: string): string => {
      if (sourceId === targetId) {
        throw new Error('Cannot create a connector from an element to itself');
      }

      const { elements } = get();
      if (!elements.has(sourceId)) {
        throw new Error(`Source element ${sourceId} does not exist`);
      }
      if (!elements.has(targetId)) {
        throw new Error(`Target element ${targetId} does not exist`);
      }

      pushHistory();

      const id = uuidv4();
      const connector: Connector = {
        id,
        sourceId,
        targetId,
        connectionType: connectionType ?? 'triggers',
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
      pushHistory();
      set((state) => {
        const next = new Map(state.connectors);
        next.set(id, { ...state.connectors.get(id)!, connectionType });
        return { connectors: next };
      });
    },

    removeConnector: (id: string): void => {
      if (!get().connectors.has(id)) return;
      pushHistory();
      set((state) => {
        const next = new Map(state.connectors);
        next.delete(id);
        return { connectors: next };
      });
    },

    // --- Viewport state ---
    viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },

    pan: (dx: number, dy: number): void => {
      set((state) => ({
        viewport: {
          ...state.viewport,
          offsetX: state.viewport.offsetX + dx,
          offsetY: state.viewport.offsetY + dy,
        },
      }));
    },

    zoom: (factor: number, center: Point): void => {
      set((state) => ({
        viewport: zoomAtPoint(state.viewport, factor, center),
      }));
    },

    // --- UI state ---
    activeTool: 'pointer' as Tool,
    selectedElementId: null,
    selectedConnectorId: null,
    pendingConnectorSourceId: null,

    setActiveTool: (tool: Tool): void => {
      set({ activeTool: tool });
    },

    selectElement: (id: string | null): void => {
      set({ selectedElementId: id, selectedConnectorId: null });
    },

    selectConnector: (id: string | null): void => {
      set({ selectedConnectorId: id, selectedElementId: null });
    },

    // --- History (undo/redo) ---
    canUndo: false,
    canRedo: false,
    _undoStack: [],
    _redoStack: [],

    undo: (): void => {
      const { _undoStack, _redoStack, elements, connectors, canvasObjects, objectGroups } = get();
      if (_undoStack.length === 0) return;
      const currentSnapshot = takeSnapshot({ elements, connectors, canvasObjects, objectGroups });
      const newRedoStack = [..._redoStack, currentSnapshot];

      const previous = _undoStack[_undoStack.length - 1];
      const newUndoStack = _undoStack.slice(0, -1);

      set({
        elements: cloneMap(previous.elements),
        connectors: cloneMap(previous.connectors),
        canvasObjects: cloneMap(previous.canvasObjects),
        objectGroups: cloneMap(previous.objectGroups),
        _undoStack: newUndoStack,
        _redoStack: newRedoStack,
        canUndo: newUndoStack.length > 0,
        canRedo: true,
      });
    },

    redo: (): void => {
      const { _undoStack, _redoStack, elements, connectors, canvasObjects, objectGroups } = get();
      if (_redoStack.length === 0) return;
      const currentSnapshot = takeSnapshot({ elements, connectors, canvasObjects, objectGroups });
      const newUndoStack = [..._undoStack, currentSnapshot];

      const next = _redoStack[_redoStack.length - 1];
      const newRedoStack = _redoStack.slice(0, -1);

      set({
        elements: cloneMap(next.elements),
        connectors: cloneMap(next.connectors),
        canvasObjects: cloneMap(next.canvasObjects),
        objectGroups: cloneMap(next.objectGroups),
        _undoStack: newUndoStack,
        _redoStack: newRedoStack,
        canUndo: true,
        canRedo: newRedoStack.length > 0,
      });
    },

    beginDragGesture: (): void => {
      pushHistory();
    },

    // --- Project state ---
    projectName: '',
    environments: [] as EnvironmentConfig[],

    setProjectName: (name: string): void => {
      set({ projectName: name });
    },

    setEnvironments: (envs: EnvironmentConfig[]): void => {
      set({ environments: envs });
    },

    // --- Terraform variables ---
    globalTerraformConfig: { ...DEFAULT_GLOBAL_CONFIG },

    setTerraformVariable: (objectId: string, varName: string, value: string | number | boolean): void => {
      const existing = get().canvasObjects.get(objectId);
      if (!existing || existing.objectType !== 'architecture-block') return;
      pushHistory();
      set((state) => {
        const next = new Map(state.canvasObjects);
        const block = state.canvasObjects.get(objectId) as ArchitectureBlock;
        next.set(objectId, {
          ...block,
          terraformVariables: { ...block.terraformVariables, [varName]: value },
        });
        return { canvasObjects: next };
      });
    },

    setTerraformVariables: (objectId: string, vars: Record<string, string | number | boolean>): void => {
      const existing = get().canvasObjects.get(objectId);
      if (!existing || existing.objectType !== 'architecture-block') return;
      pushHistory();
      set((state) => {
        const next = new Map(state.canvasObjects);
        const block = state.canvasObjects.get(objectId) as ArchitectureBlock;
        next.set(objectId, {
          ...block,
          terraformVariables: { ...block.terraformVariables, ...vars },
        });
        return { canvasObjects: next };
      });
    },

    updateGlobalTerraformConfig: (updates: Partial<GlobalTerraformConfig>): void => {
      set((state) => ({
        globalTerraformConfig: { ...state.globalTerraformConfig, ...updates },
      }));
    },

    // --- Serialization ---

    serializeDiagramState: (): DiagramState => {
      const { elements, connectors, viewport, projectName, environments, canvasObjects, objectGroups, globalTerraformConfig } = get();

      const serializedCanvasObjects: SerializedCanvasObject[] = Array.from(canvasObjects.values()).map((obj) => {
        const base: SerializedCanvasObject = {
          id: obj.id,
          objectType: obj.objectType,
          name: obj.name,
          visualConfig: { ...obj.visualConfig } as Record<string, unknown>,
          zIndex: obj.zIndex,
          ...(obj.groupId !== undefined && { groupId: obj.groupId }),
        };

        if (obj.objectType === 'architecture-block') {
          base.x = obj.position.x;
          base.y = obj.position.y;
          base.serviceType = obj.serviceType;
          base.config = { ...obj.config };
          base.terraformVariables = { ...obj.terraformVariables };
        } else if (obj.objectType === 'line') {
          base.startX = obj.start.x;
          base.startY = obj.start.y;
          base.endX = obj.end.x;
          base.endY = obj.end.y;
          base.sourceAnchorObjectId = obj.sourceAnchor ? obj.sourceAnchor.objectId : null;
          base.targetAnchorObjectId = obj.targetAnchor ? obj.targetAnchor.objectId : null;
          base.sourceAnchorPosition = obj.sourceAnchor ? obj.sourceAnchor.anchorPosition : null;
          base.targetAnchorPosition = obj.targetAnchor ? obj.targetAnchor.anchorPosition : null;
          if (obj.waypoints && obj.waypoints.length > 0) {
            base.waypoints = obj.waypoints.map((wp) => ({ x: wp.x, y: wp.y }));
          }
        } else if (obj.objectType === 'geometric') {
          base.x = obj.position.x;
          base.y = obj.position.y;
        } else if (obj.objectType === 'text') {
          base.x = obj.position.x;
          base.y = obj.position.y;
          base.content = obj.content;
        } else if (obj.objectType === 'uml') {
          base.x = obj.position.x;
          base.y = obj.position.y;
          base.umlKind = obj.umlKind;
          if (obj.classData) {
            base.classData = { ...obj.classData, attributes: [...obj.classData.attributes], methods: [...obj.classData.methods] };
          }
        }

        return base;
      });

      const serializedGroups = Array.from(objectGroups.values()).map((g) => ({
        id: g.id,
        name: g.name,
        memberIds: [...g.memberIds],
      }));

      return {
        version: CURRENT_DIAGRAM_VERSION,
        projectName,
        environments: environments.map((e) => ({ ...e, variables: { ...e.variables } })),
        elements: Array.from(elements.values()).map((el) => ({
          id: el.id,
          serviceType: el.serviceType,
          name: el.name,
          position: { ...el.position },
          config: { ...el.config },
        })),
        canvasObjects: serializedCanvasObjects,
        connectors: Array.from(connectors.values()).map((c) => ({
          id: c.id,
          sourceId: c.sourceId,
          targetId: c.targetId,
          connectionType: c.connectionType,
        })),
        viewport: { ...viewport },
        ...(serializedGroups.length > 0 && { objectGroups: serializedGroups }),
        globalTerraformConfig: { ...globalTerraformConfig },
        globalRoutingMode: get().globalRoutingMode,
      };
    },

    loadDiagramState: (state: DiagramState): void => {
      const elementsMap = new Map<string, DiagramElement>();
      for (const el of state.elements) {
        elementsMap.set(el.id, {
          id: el.id,
          serviceType: el.serviceType,
          name: el.name,
          position: { ...el.position },
          config: { ...el.config },
        });
      }

      const connectorsMap = new Map<string, Connector>();
      for (const c of state.connectors) {
        connectorsMap.set(c.id, {
          id: c.id,
          sourceId: c.sourceId,
          targetId: c.targetId,
          connectionType: c.connectionType,
        });
      }

      // Deserialize canvasObjects
      const canvasObjectsMap = new Map<string, CanvasObject>();
      const isV2 = state.version === 2;

      // Valid geometric shapes for fallback
      const VALID_GEOMETRIC_SHAPES: Set<string> = new Set([
        'rectangle', 'rounded-rectangle', 'ellipse', 'circle',
        'triangle', 'diamond', 'parallelogram', 'trapezoid',
        'hexagon', 'octagon', 'pentagon', 'star', 'cross',
        'arrow-right', 'arrow-left', 'arrow-up', 'arrow-down',
        'chevron', 'cylinder', 'cloud', 'callout',
        'document', 'process', 'decision', 'data', 'predefined-process',
      ]);

      const VALID_UML_KINDS: Set<string> = new Set([
        'class', 'interface', 'actor', 'use-case', 'component', 'package', 'node',
      ]);

      if (state.canvasObjects && state.canvasObjects.length > 0) {
        for (let i = 0; i < state.canvasObjects.length; i++) {
          const sObj = state.canvasObjects[i];
          const zIndex = (sObj as unknown as Record<string, unknown>).zIndex as number ?? i;
          const groupId = (sObj as unknown as Record<string, unknown>).groupId as string | undefined;
          if (sObj.objectType === 'architecture-block') {
            const obj: ArchitectureBlock = {
              id: sObj.id,
              objectType: 'architecture-block',
              name: sObj.name,
              position: { x: sObj.x ?? 0, y: sObj.y ?? 0 },
              serviceType: sObj.serviceType!,
              config: sObj.config ? { ...sObj.config } : {},
              terraformVariables: sObj.terraformVariables
                ? { ...sObj.terraformVariables }
                : getDefaultVariables(sObj.serviceType!),
              visualConfig: {
                width: (sObj.visualConfig.width as number) ?? DEFAULT_BLOCK_VISUAL.width,
                height: (sObj.visualConfig.height as number) ?? DEFAULT_BLOCK_VISUAL.height,
              },
              zIndex,
              ...(groupId !== undefined && { groupId }),
            };
            canvasObjectsMap.set(obj.id, obj);
          } else if (sObj.objectType === 'line') {
            // v2→v3 migration: lines without anchor fields get null anchors
            const sourceAnchor: AnchorRef | null = sObj.sourceAnchorObjectId
              ? { objectId: sObj.sourceAnchorObjectId, anchorPosition: (sObj.sourceAnchorPosition as AnchorPosition) ?? 'right' }
              : null;
            const targetAnchor: AnchorRef | null = sObj.targetAnchorObjectId
              ? { objectId: sObj.targetAnchorObjectId, anchorPosition: (sObj.targetAnchorPosition as AnchorPosition) ?? 'left' }
              : null;
            // Deserialize waypoints: validate shape, treat malformed data as null
            let waypoints: Point[] | null = null;
            if (Array.isArray(sObj.waypoints)) {
              const valid = sObj.waypoints.every(
                (wp): wp is { x: number; y: number } =>
                  wp != null && typeof wp === 'object' && typeof wp.x === 'number' && typeof wp.y === 'number' && isFinite(wp.x) && isFinite(wp.y)
              );
              if (valid && sObj.waypoints.length > 0) {
                waypoints = sObj.waypoints.map((wp) => ({ x: wp.x, y: wp.y }));
              }
            }
            const obj: LineObject = {
              id: sObj.id,
              objectType: 'line',
              name: sObj.name,
              start: { x: sObj.startX ?? 0, y: sObj.startY ?? 0 },
              end: { x: sObj.endX ?? 0, y: sObj.endY ?? 0 },
              sourceAnchor,
              targetAnchor,
              waypoints,
              visualConfig: {
                color: (sObj.visualConfig.color as string) ?? DEFAULT_LINE_VISUAL.color,
                borderWidth: (sObj.visualConfig.borderWidth as number) ?? DEFAULT_LINE_VISUAL.borderWidth,
                strokeStyle: (sObj.visualConfig.strokeStyle as 'solid' | 'dashed') ?? DEFAULT_LINE_VISUAL.strokeStyle,
                startArrow: (sObj.visualConfig.startArrow as boolean) ?? DEFAULT_LINE_VISUAL.startArrow,
                endArrow: (sObj.visualConfig.endArrow as boolean) ?? DEFAULT_LINE_VISUAL.endArrow,
                routingMode: (sObj.visualConfig.routingMode as RoutingMode) ?? DEFAULT_LINE_VISUAL.routingMode,
              },
              zIndex,
              ...(groupId !== undefined && { groupId }),
            };
            canvasObjectsMap.set(obj.id, obj);
          } else if (sObj.objectType === 'geometric') {
            // Validate shape, fall back to rectangle for unknown shapes
            const rawShape = (sObj.visualConfig.shape as string) ?? DEFAULT_GEO_VISUAL.shape;
            const shape = VALID_GEOMETRIC_SHAPES.has(rawShape) ? rawShape as GeometricShape : 'rectangle';
            const obj: GeometricObject = {
              id: sObj.id,
              objectType: 'geometric',
              name: sObj.name,
              position: { x: sObj.x ?? 0, y: sObj.y ?? 0 },
              visualConfig: {
                width: (sObj.visualConfig.width as number) ?? DEFAULT_GEO_VISUAL.width,
                height: (sObj.visualConfig.height as number) ?? DEFAULT_GEO_VISUAL.height,
                fill: (sObj.visualConfig.fill as boolean) ?? DEFAULT_GEO_VISUAL.fill,
                fillColor: (sObj.visualConfig.fillColor as string) ?? DEFAULT_GEO_VISUAL.fillColor,
                borderColor: (sObj.visualConfig.borderColor as string) ?? DEFAULT_GEO_VISUAL.borderColor,
                borderWidth: (sObj.visualConfig.borderWidth as number) ?? DEFAULT_GEO_VISUAL.borderWidth,
                shape,
              },
              zIndex,
              ...(groupId !== undefined && { groupId }),
            };
            canvasObjectsMap.set(obj.id, obj);
          } else if (sObj.objectType === 'text') {
            const obj: TextObject = {
              id: sObj.id,
              objectType: 'text',
              name: sObj.name,
              position: { x: sObj.x ?? 0, y: sObj.y ?? 0 },
              content: sObj.content ?? '',
              visualConfig: {
                width: (sObj.visualConfig.width as number) ?? DEFAULT_TEXT_VISUAL.width,
                height: (sObj.visualConfig.height as number) ?? DEFAULT_TEXT_VISUAL.height,
                fontSize: (sObj.visualConfig.fontSize as number) ?? DEFAULT_TEXT_VISUAL.fontSize,
                fontColor: (sObj.visualConfig.fontColor as string) ?? DEFAULT_TEXT_VISUAL.fontColor,
                textAlign: (sObj.visualConfig.textAlign as 'left' | 'center' | 'right') ?? DEFAULT_TEXT_VISUAL.textAlign,
                bold: (sObj.visualConfig.bold as boolean) ?? DEFAULT_TEXT_VISUAL.bold,
                italic: (sObj.visualConfig.italic as boolean) ?? DEFAULT_TEXT_VISUAL.italic,
              },
              zIndex,
              ...(groupId !== undefined && { groupId }),
            };
            canvasObjectsMap.set(obj.id, obj);
          } else if (sObj.objectType === 'uml') {
            // Validate umlKind, fall back to 'class' for unknown kinds (renders as generic rectangle)
            const rawKind = sObj.umlKind as string | undefined;
            const umlKind: UMLKind = (rawKind && VALID_UML_KINDS.has(rawKind)) ? rawKind as UMLKind : 'class';
            const obj: UMLObject = {
              id: sObj.id,
              objectType: 'uml',
              name: sObj.name,
              position: { x: sObj.x ?? 0, y: sObj.y ?? 0 },
              umlKind,
              classData: sObj.classData ? { ...sObj.classData, attributes: [...sObj.classData.attributes], methods: [...sObj.classData.methods] } : undefined,
              visualConfig: {
                width: (sObj.visualConfig.width as number) ?? DEFAULT_UML_VISUAL.width,
                height: (sObj.visualConfig.height as number) ?? DEFAULT_UML_VISUAL.height,
                fillColor: (sObj.visualConfig.fillColor as string) ?? DEFAULT_UML_VISUAL.fillColor,
                borderColor: (sObj.visualConfig.borderColor as string) ?? DEFAULT_UML_VISUAL.borderColor,
                borderWidth: (sObj.visualConfig.borderWidth as number) ?? DEFAULT_UML_VISUAL.borderWidth,
                headerColor: (sObj.visualConfig.headerColor as string) ?? DEFAULT_UML_VISUAL.headerColor,
              },
              zIndex,
              ...(groupId !== undefined && { groupId }),
            };
            canvasObjectsMap.set(obj.id, obj);
          } else {
            // Unknown objectType: skip with warning
            console.warn(`Unknown objectType "${sObj.objectType}" for object "${sObj.id}", skipping.`);
          }
        }
      } else if (!state.version || state.version === 1) {
        // v1→v2 migration: convert elements to canvasObjects with default visual configs
        let migrationIndex = 0;
        for (const el of state.elements) {
          const obj: ArchitectureBlock = {
            id: el.id,
            objectType: 'architecture-block',
            serviceType: el.serviceType,
            name: el.name,
            position: { ...el.position },
            config: { ...el.config },
            terraformVariables: getDefaultVariables(el.serviceType),
            visualConfig: { ...DEFAULT_BLOCK_VISUAL },
            zIndex: migrationIndex++,
          };
          canvasObjectsMap.set(obj.id, obj);
        }
      }

      // Deserialize objectGroups
      const objectGroupsMap = new Map<string, ObjectGroup>();
      if (state.objectGroups && state.objectGroups.length > 0) {
        for (const g of state.objectGroups) {
          objectGroupsMap.set(g.id, {
            id: g.id,
            name: g.name,
            memberIds: [...g.memberIds],
          });
        }
      }

      set({
        elements: elementsMap,
        connectors: connectorsMap,
        canvasObjects: canvasObjectsMap,
        viewport: { ...state.viewport },
        projectName: state.projectName,
        environments: state.environments.map((e) => ({ ...e, variables: { ...e.variables } })),
        selectedObjectIds: new Set(),
        objectGroups: objectGroupsMap,
        globalTerraformConfig: state.globalTerraformConfig
          ? { ...state.globalTerraformConfig }
          : { ...DEFAULT_GLOBAL_CONFIG },
        globalRoutingMode: (state.globalRoutingMode as RoutingMode) ?? 'orthogonal',
        _undoStack: [],
        _redoStack: [],
        canUndo: false,
        canRedo: false,
      });
    },

    serializeToArchitectureDescription: (): ArchitectureDescription => {
      const { elements, canvasObjects, connectors, projectName, environments, globalTerraformConfig } = get();

      // Use canvasObjects (architecture blocks) as the source of resources
      const resources = Array.from(canvasObjects.values())
        .filter((obj): obj is ArchitectureBlock => obj.objectType === 'architecture-block')
        .map((block) => ({
          name: block.name,
          service_type: block.serviceType,
          config: { ...block.config },
          terraform_variables: { ...block.terraformVariables },
        }));

      // Build a name lookup from canvasObjects and elements for connector resolution
      const nameById = new Map<string, string>();
      for (const obj of canvasObjects.values()) {
        nameById.set(obj.id, obj.name);
      }
      // Fallback to elements for backward compatibility
      for (const el of elements.values()) {
        if (!nameById.has(el.id)) {
          nameById.set(el.id, el.name);
        }
      }

      const connections = Array.from(connectors.values()).map((c) => ({
        source: nameById.get(c.sourceId) ?? '',
        target: nameById.get(c.targetId) ?? '',
        connection_type: c.connectionType,
      }));

      return {
        project_name: projectName,
        environments: environments.map((e) => ({
          name: e.name,
          variables: { ...e.variables },
        })),
        resources,
        connections,
        global_terraform_config: {
          backend_type: globalTerraformConfig.backend.type,
          backend_config: { ...globalTerraformConfig.backend.config },
          provider_region: globalTerraformConfig.provider.region,
          ...(globalTerraformConfig.provider.profile && { provider_profile: globalTerraformConfig.provider.profile }),
          ...(globalTerraformConfig.versionConstraints.terraformVersion && { terraform_version: globalTerraformConfig.versionConstraints.terraformVersion }),
          ...(globalTerraformConfig.versionConstraints.awsProviderVersion && { aws_provider_version: globalTerraformConfig.versionConstraints.awsProviderVersion }),
        },
      };
    },

    // --- Server persistence ---
    currentDiagramId: null,
    diagramSummaries: [] as DiagramSummary[],
    isSaving: false,
    isLoading: false,

    saveDiagramToServer: async (): Promise<void> => {
      const toast = useToastStore.getState();
      set({ isSaving: true });
      try {
        const state = get().serializeDiagramState();
        const result = await apiClient.saveDiagram(state);
        if (result.ok) {
          set({ currentDiagramId: result.data.id });
          toast.addToast('Diagram saved', 'success');
        } else {
          toast.addToast(result.error.message, 'error');
        }
      } finally {
        set({ isSaving: false });
      }
    },

    updateDiagramOnServer: async (id: string): Promise<void> => {
      const toast = useToastStore.getState();
      set({ isSaving: true });
      try {
        const state = get().serializeDiagramState();
        const result = await apiClient.updateDiagram(id, state);
        if (result.ok) {
          toast.addToast('Diagram updated', 'success');
        } else {
          toast.addToast(result.error.message, 'error');
        }
      } finally {
        set({ isSaving: false });
      }
    },

    loadDiagramFromServer: async (id: string): Promise<void> => {
      const toast = useToastStore.getState();
      set({ isLoading: true });
      try {
        const result = await apiClient.loadDiagram(id);
        if (result.ok) {
          get().loadDiagramState(result.data as DiagramState);
          set({ currentDiagramId: id });
        } else {
          toast.addToast(result.error.message, 'error');
        }
      } finally {
        set({ isLoading: false });
      }
    },

    listDiagramsFromServer: async (): Promise<DiagramSummary[]> => {
      const toast = useToastStore.getState();
      set({ isLoading: true });
      try {
        const result = await apiClient.listDiagrams();
        if (result.ok) {
          set({ diagramSummaries: result.data });
          return result.data;
        } else {
          toast.addToast(result.error.message, 'error');
          return [];
        }
      } finally {
        set({ isLoading: false });
      }
    },

    deleteDiagramFromServer: async (id: string): Promise<void> => {
      const toast = useToastStore.getState();
      try {
        const result = await apiClient.deleteDiagram(id);
        if (result.ok) {
          toast.addToast('Diagram deleted', 'success');
          if (get().currentDiagramId === id) {
            set({ currentDiagramId: null });
          }
          set((state) => ({
            diagramSummaries: state.diagramSummaries.filter((s) => s.diagram_id !== id),
          }));
        } else {
          toast.addToast(result.error.message, 'error');
        }
      } catch {
        toast.addToast('Failed to delete diagram', 'error');
      }
    },

    // --- Bottom panel state ---
    bottomPanelExpanded: false,
    bottomPanelHeight: DEFAULT_PANEL_HEIGHT,

    setBottomPanelExpanded: (expanded: boolean): void => {
      set({ bottomPanelExpanded: expanded });
    },

    setBottomPanelHeight: (height: number): void => {
      const maxHeight = MAX_PANEL_HEIGHT_RATIO * window.innerHeight;
      const clamped = Math.min(Math.max(height, MIN_PANEL_HEIGHT), maxHeight);
      set({ bottomPanelHeight: clamped });
    },

    toggleBottomPanel: (): void => {
      set((state) => ({ bottomPanelExpanded: !state.bottomPanelExpanded }));
    },

    // --- Sidebar panel state ---
    sidebarExpanded: false,
    sidebarWidth: DEFAULT_SIDEBAR_WIDTH,

    setSidebarExpanded: (expanded: boolean): void => {
      set({ sidebarExpanded: expanded });
    },

    setSidebarWidth: (width: number): void => {
      const maxWidth = MAX_SIDEBAR_WIDTH_RATIO * window.innerWidth;
      const clamped = Math.min(Math.max(width, MIN_SIDEBAR_WIDTH), maxWidth);
      set({ sidebarWidth: clamped });
    },

    toggleSidebar: (): void => {
      set((state) => ({ sidebarExpanded: !state.sidebarExpanded }));
    },

    // --- Global routing mode ---
    globalRoutingMode: 'orthogonal' as RoutingMode,

    setGlobalRoutingMode: (mode: RoutingMode): void => {
      set({ globalRoutingMode: mode });
    },
  };
});
