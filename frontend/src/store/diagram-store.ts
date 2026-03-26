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
} from '@/types/diagram';
import type { DiagramState, ArchitectureDescription } from '@/types/serialization';
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
      const { elements, connectors, viewport, projectName, environments } = get();
      return {
        version: 1,
        projectName,
        environments: environments.map((e) => ({ ...e, variables: { ...e.variables } })),
        elements: Array.from(elements.values()).map((el) => ({
          id: el.id,
          serviceType: el.serviceType,
          name: el.name,
          position: { ...el.position },
          config: { ...el.config },
        })),
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

      set({
        elements: elementsMap,
        connectors: connectorsMap,
        viewport: { ...state.viewport },
        projectName: state.projectName,
        environments: state.environments.map((e) => ({ ...e, variables: { ...e.variables } })),
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
