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
  ArchitectureBlock,
  LineObject,
  GeometricObject,
  ArchitectureBlockVisualConfig,
  LineVisualConfig,
  GeometricVisualConfig,
} from '@/types/diagram';
import {
  MIN_OBJECT_WIDTH,
  MIN_OBJECT_HEIGHT,
  DEFAULT_BLOCK_VISUAL,
  DEFAULT_LINE_VISUAL,
  DEFAULT_GEO_VISUAL,
} from '@/types/diagram';
import type { DiagramState, ArchitectureDescription, SerializedCanvasObject } from '@/types/serialization';
import type { DiagramSummary } from '@/types/api';
import { zoomAtPoint } from '@/utils/viewport';
import { apiClient } from '@/utils/api-client';
import { useToastStore } from '@/store/toast-store';

interface HistoryEntry {
  elements: Map<string, DiagramElement>;
  connectors: Map<string, Connector>;
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

function takeSnapshot(state: { elements: Map<string, DiagramElement>; connectors: Map<string, Connector> }): HistoryEntry {
  return {
    elements: cloneMap(state.elements),
    connectors: cloneMap(state.connectors),
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
  selectedObjectId: string | null;
  addCanvasObject: (obj: Omit<CanvasObject, 'id'>) => string;
  updateCanvasObject: (id: string, updates: Partial<CanvasObject>) => void;
  removeCanvasObject: (id: string) => void;
  selectObject: (id: string | null) => void;
  updateVisualConfig: (id: string, config: Partial<ArchitectureBlockVisualConfig | LineVisualConfig | GeometricVisualConfig>) => void;
  updateObjectBounds: (id: string, bounds: { width?: number; height?: number }) => void;
  updateLineEndpoint: (id: string, endpoint: 'start' | 'end', position: Point) => void;

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

  // Project state
  projectName: string;
  environments: EnvironmentConfig[];
  setProjectName: (name: string) => void;
  setEnvironments: (envs: EnvironmentConfig[]) => void;

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

  /** @internal — exposed for testing reset only */
  _undoStack: HistoryEntry[];
  _redoStack: HistoryEntry[];
}

export const useDiagramStore = create<DiagramStore>((set, get) => {
  function pushHistory() {
    const { elements, connectors, _undoStack } = get();
    const snapshot = takeSnapshot({ elements, connectors });
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
    selectedObjectId: null as string | null,

    addCanvasObject: (obj: Omit<CanvasObject, 'id'>): string => {
      const id = uuidv4();
      const canvasObject = { ...obj, id } as CanvasObject;

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
        const nextSelectedObjectId = state.selectedObjectId === id ? null : state.selectedObjectId;

        return { canvasObjects: next, connectors: nextConnectors, selectedObjectId: nextSelectedObjectId };
      });
    },

    selectObject: (id: string | null): void => {
      set({ selectedObjectId: id });
    },

    updateVisualConfig: (id: string, config: Partial<ArchitectureBlockVisualConfig | LineVisualConfig | GeometricVisualConfig>): void => {
      const existing = get().canvasObjects.get(id);
      if (!existing) return;

      const mergedConfig = { ...existing.visualConfig, ...config };

      // Enforce minimum dimensions for object types with width/height
      if (existing.objectType === 'architecture-block' || existing.objectType === 'geometric') {
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

      const updated = { ...existing, [endpoint]: { ...position } };

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, updated);
        return { canvasObjects: next };
      });
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
      const { _undoStack, _redoStack, elements, connectors } = get();
      if (_undoStack.length === 0) return;
      const currentSnapshot = takeSnapshot({ elements, connectors });
      const newRedoStack = [..._redoStack, currentSnapshot];

      const previous = _undoStack[_undoStack.length - 1];
      const newUndoStack = _undoStack.slice(0, -1);

      set({
        elements: cloneMap(previous.elements),
        connectors: cloneMap(previous.connectors),
        _undoStack: newUndoStack,
        _redoStack: newRedoStack,
        canUndo: newUndoStack.length > 0,
        canRedo: true,
      });
    },

    redo: (): void => {
      const { _undoStack, _redoStack, elements, connectors } = get();
      if (_redoStack.length === 0) return;
      const currentSnapshot = takeSnapshot({ elements, connectors });
      const newUndoStack = [..._undoStack, currentSnapshot];

      const next = _redoStack[_redoStack.length - 1];
      const newRedoStack = _redoStack.slice(0, -1);

      set({
        elements: cloneMap(next.elements),
        connectors: cloneMap(next.connectors),
        _undoStack: newUndoStack,
        _redoStack: newRedoStack,
        canUndo: true,
        canRedo: newRedoStack.length > 0,
      });
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

    // --- Serialization ---

    serializeDiagramState: (): DiagramState => {
      const { elements, connectors, viewport, projectName, environments, canvasObjects } = get();

      const serializedCanvasObjects: SerializedCanvasObject[] = Array.from(canvasObjects.values()).map((obj) => {
        const base: SerializedCanvasObject = {
          id: obj.id,
          objectType: obj.objectType,
          name: obj.name,
          visualConfig: { ...obj.visualConfig } as Record<string, unknown>,
        };

        if (obj.objectType === 'architecture-block') {
          base.x = obj.position.x;
          base.y = obj.position.y;
          base.serviceType = obj.serviceType;
          base.config = { ...obj.config };
        } else if (obj.objectType === 'line') {
          base.startX = obj.start.x;
          base.startY = obj.start.y;
          base.endX = obj.end.x;
          base.endY = obj.end.y;
        } else if (obj.objectType === 'geometric') {
          base.x = obj.position.x;
          base.y = obj.position.y;
        }

        return base;
      });

      return {
        version: 2,
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

      if (state.canvasObjects && state.canvasObjects.length > 0) {
        // v2 format: deserialize canvasObjects from the serialized array
        for (const sObj of state.canvasObjects) {
          if (sObj.objectType === 'architecture-block') {
            const obj: ArchitectureBlock = {
              id: sObj.id,
              objectType: 'architecture-block',
              name: sObj.name,
              position: { x: sObj.x ?? 0, y: sObj.y ?? 0 },
              serviceType: sObj.serviceType!,
              config: sObj.config ? { ...sObj.config } : {},
              visualConfig: {
                width: (sObj.visualConfig.width as number) ?? DEFAULT_BLOCK_VISUAL.width,
                height: (sObj.visualConfig.height as number) ?? DEFAULT_BLOCK_VISUAL.height,
              },
            };
            canvasObjectsMap.set(obj.id, obj);
          } else if (sObj.objectType === 'line') {
            const obj: LineObject = {
              id: sObj.id,
              objectType: 'line',
              name: sObj.name,
              start: { x: sObj.startX ?? 0, y: sObj.startY ?? 0 },
              end: { x: sObj.endX ?? 0, y: sObj.endY ?? 0 },
              visualConfig: {
                color: (sObj.visualConfig.color as string) ?? DEFAULT_LINE_VISUAL.color,
                borderWidth: (sObj.visualConfig.borderWidth as number) ?? DEFAULT_LINE_VISUAL.borderWidth,
                strokeStyle: (sObj.visualConfig.strokeStyle as 'solid' | 'dashed') ?? DEFAULT_LINE_VISUAL.strokeStyle,
                startArrow: (sObj.visualConfig.startArrow as boolean) ?? DEFAULT_LINE_VISUAL.startArrow,
                endArrow: (sObj.visualConfig.endArrow as boolean) ?? DEFAULT_LINE_VISUAL.endArrow,
              },
            };
            canvasObjectsMap.set(obj.id, obj);
          } else if (sObj.objectType === 'geometric') {
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
                shape: (sObj.visualConfig.shape as 'rectangle' | 'ellipse') ?? DEFAULT_GEO_VISUAL.shape,
              },
            };
            canvasObjectsMap.set(obj.id, obj);
          }
        }
      } else if (!state.version || state.version === 1) {
        // v1→v2 migration: convert elements to canvasObjects with default visual configs
        for (const el of state.elements) {
          const obj: ArchitectureBlock = {
            id: el.id,
            objectType: 'architecture-block',
            serviceType: el.serviceType,
            name: el.name,
            position: { ...el.position },
            config: { ...el.config },
            visualConfig: { ...DEFAULT_BLOCK_VISUAL },
          };
          canvasObjectsMap.set(obj.id, obj);
        }
      }

      set({
        elements: elementsMap,
        connectors: connectorsMap,
        canvasObjects: canvasObjectsMap,
        viewport: { ...state.viewport },
        projectName: state.projectName,
        environments: state.environments.map((e) => ({ ...e, variables: { ...e.variables } })),
        selectedObjectId: null,
        _undoStack: [],
        _redoStack: [],
        canUndo: false,
        canRedo: false,
      });
    },

    serializeToArchitectureDescription: (): ArchitectureDescription => {
      const { elements, connectors, projectName, environments } = get();

      const resources = Array.from(elements.values()).map((el) => ({
        name: el.name,
        service_type: el.serviceType,
        config: { ...el.config },
      }));

      const connections = Array.from(connectors.values()).map((c) => {
        const source = elements.get(c.sourceId);
        const target = elements.get(c.targetId);
        return {
          source: source?.name ?? '',
          target: target?.name ?? '',
          connection_type: c.connectionType,
        };
      });

      return {
        project_name: projectName,
        environments: environments.map((e) => ({
          name: e.name,
          variables: { ...e.variables },
        })),
        resources,
        connections,
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
  };
});
