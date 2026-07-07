import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import { useToastStore } from '@/store/toast-store';
import { apiClient } from '@/utils/api-client';

vi.mock('@/utils/api-client', () => ({
  apiClient: {
    saveDiagram: vi.fn(),
    updateDiagram: vi.fn(),
    loadDiagram: vi.fn(),
    listDiagrams: vi.fn(),
    deleteDiagram: vi.fn(),
  },
}));

function resetStore() {
  useDiagramStore.setState({
    connectors: new Map(),
    viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    projectName: 'test-project',
    environments: [],
    currentDiagramId: null,
    diagramSummaries: [],
    isSaving: false,
    isLoading: false,
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

describe('DiagramStore - Server Persistence State', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('has default currentDiagramId of null', () => {
    expect(useDiagramStore.getState().currentDiagramId).toBeNull();
  });

  it('has default diagramSummaries as empty array', () => {
    expect(useDiagramStore.getState().diagramSummaries).toEqual([]);
  });

  it('has default isSaving of false', () => {
    expect(useDiagramStore.getState().isSaving).toBe(false);
  });

  it('has default isLoading of false', () => {
    expect(useDiagramStore.getState().isLoading).toBe(false);
  });
});

describe('DiagramStore - saveDiagramToServer', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('calls apiClient.saveDiagram with serialized state and stores returned id', async () => {
    vi.mocked(apiClient.saveDiagram).mockResolvedValue({ ok: true, data: { id: 'diagram-123' } });

    await useDiagramStore.getState().saveDiagramToServer();

    expect(apiClient.saveDiagram).toHaveBeenCalledTimes(1);
    const arg = vi.mocked(apiClient.saveDiagram).mock.calls[0][0];
    expect(arg.projectName).toBe('test-project');
    expect(useDiagramStore.getState().currentDiagramId).toBe('diagram-123');
  });

  it('shows success toast on save', async () => {
    vi.mocked(apiClient.saveDiagram).mockResolvedValue({ ok: true, data: { id: 'diagram-123' } });
    const addToast = vi.spyOn(useToastStore.getState(), 'addToast');

    await useDiagramStore.getState().saveDiagramToServer();

    expect(addToast).toHaveBeenCalledWith('Diagram saved', 'success');
  });

  it('shows error toast on failure', async () => {
    vi.mocked(apiClient.saveDiagram).mockResolvedValue({
      ok: false,
      error: { type: 'network', message: 'Server unreachable' },
    });
    const addToast = vi.spyOn(useToastStore.getState(), 'addToast');

    await useDiagramStore.getState().saveDiagramToServer();

    expect(addToast).toHaveBeenCalledWith('Server unreachable', 'error');
    expect(useDiagramStore.getState().currentDiagramId).toBeNull();
  });

  it('sets isSaving during operation', async () => {
    let resolveFn: (v: any) => void;
    vi.mocked(apiClient.saveDiagram).mockReturnValue(
      new Promise((resolve) => { resolveFn = resolve; }),
    );

    const promise = useDiagramStore.getState().saveDiagramToServer();
    expect(useDiagramStore.getState().isSaving).toBe(true);

    resolveFn!({ ok: true, data: { id: 'x' } });
    await promise;
    expect(useDiagramStore.getState().isSaving).toBe(false);
  });
});

describe('DiagramStore - updateDiagramOnServer', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('calls apiClient.updateDiagram with id and serialized state', async () => {
    vi.mocked(apiClient.updateDiagram).mockResolvedValue({ ok: true, data: undefined });

    await useDiagramStore.getState().updateDiagramOnServer('diagram-456');

    expect(apiClient.updateDiagram).toHaveBeenCalledTimes(1);
    expect(vi.mocked(apiClient.updateDiagram).mock.calls[0][0]).toBe('diagram-456');
  });

  it('shows success toast on update', async () => {
    vi.mocked(apiClient.updateDiagram).mockResolvedValue({ ok: true, data: undefined });
    const addToast = vi.spyOn(useToastStore.getState(), 'addToast');

    await useDiagramStore.getState().updateDiagramOnServer('diagram-456');

    expect(addToast).toHaveBeenCalledWith('Diagram updated', 'success');
  });

  it('shows error toast on failure', async () => {
    vi.mocked(apiClient.updateDiagram).mockResolvedValue({
      ok: false,
      error: { type: 'http', status: 403, message: 'Forbidden' },
    });
    const addToast = vi.spyOn(useToastStore.getState(), 'addToast');

    await useDiagramStore.getState().updateDiagramOnServer('diagram-456');

    expect(addToast).toHaveBeenCalledWith('Forbidden', 'error');
  });

  it('sets isSaving during operation', async () => {
    let resolveFn: (v: any) => void;
    vi.mocked(apiClient.updateDiagram).mockReturnValue(
      new Promise((resolve) => { resolveFn = resolve; }),
    );

    const promise = useDiagramStore.getState().updateDiagramOnServer('id');
    expect(useDiagramStore.getState().isSaving).toBe(true);

    resolveFn!({ ok: true, data: undefined });
    await promise;
    expect(useDiagramStore.getState().isSaving).toBe(false);
  });
});

describe('DiagramStore - loadDiagramFromServer', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('calls apiClient.loadDiagram and loads state on success', async () => {
    const diagramState = {
      version: 1,
      projectName: 'loaded-project',
      environments: [],
      canvasObjects: [
        { id: 'e1', objectType: 'architecture-block', serviceType: 'lambda', name: 'lambda-1', x: 10, y: 20, config: {}, visualConfig: { width: 80, height: 80 } },
      ],
      connectors: [],
      viewport: { offsetX: 5, offsetY: 10, scale: 1.5 },
    };
    vi.mocked(apiClient.loadDiagram).mockResolvedValue({ ok: true, data: diagramState });

    await useDiagramStore.getState().loadDiagramFromServer('diagram-789');

    expect(apiClient.loadDiagram).toHaveBeenCalledWith('diagram-789');
    expect(useDiagramStore.getState().currentDiagramId).toBe('diagram-789');
    expect(useDiagramStore.getState().projectName).toBe('loaded-project');
    expect(useDiagramStore.getState().canvasObjects.size).toBe(1);
  });

  it('shows error toast on failure without changing state', async () => {
    vi.mocked(apiClient.loadDiagram).mockResolvedValue({
      ok: false,
      error: { type: 'http', status: 404, message: 'Diagram not found' },
    });
    const addToast = vi.spyOn(useToastStore.getState(), 'addToast');

    await useDiagramStore.getState().loadDiagramFromServer('nonexistent');

    expect(addToast).toHaveBeenCalledWith('Diagram not found', 'error');
    expect(useDiagramStore.getState().currentDiagramId).toBeNull();
  });

  it('sets isLoading during operation', async () => {
    let resolveFn: (v: any) => void;
    vi.mocked(apiClient.loadDiagram).mockReturnValue(
      new Promise((resolve) => { resolveFn = resolve; }),
    );

    const promise = useDiagramStore.getState().loadDiagramFromServer('id');
    expect(useDiagramStore.getState().isLoading).toBe(true);

    resolveFn!({ ok: true, data: { version: 2, projectName: '', environments: [], canvasObjects: [], connectors: [], viewport: { offsetX: 0, offsetY: 0, scale: 1 } } });
    await promise;
    expect(useDiagramStore.getState().isLoading).toBe(false);
  });
});

describe('DiagramStore - listDiagramsFromServer', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('calls apiClient.listDiagrams and stores summaries', async () => {
    const summaries = [
      { diagram_id: 'd1', project_name: 'Project A', updated_at: '2024-01-01T00:00:00Z' },
      { diagram_id: 'd2', project_name: 'Project B', updated_at: '2024-01-02T00:00:00Z' },
    ];
    vi.mocked(apiClient.listDiagrams).mockResolvedValue({ ok: true, data: summaries });

    const result = await useDiagramStore.getState().listDiagramsFromServer();

    expect(apiClient.listDiagrams).toHaveBeenCalledTimes(1);
    expect(result).toEqual(summaries);
    expect(useDiagramStore.getState().diagramSummaries).toEqual(summaries);
  });

  it('shows error toast and returns empty array on failure', async () => {
    vi.mocked(apiClient.listDiagrams).mockResolvedValue({
      ok: false,
      error: { type: 'network', message: 'Network request failed' },
    });
    const addToast = vi.spyOn(useToastStore.getState(), 'addToast');

    const result = await useDiagramStore.getState().listDiagramsFromServer();

    expect(addToast).toHaveBeenCalledWith('Network request failed', 'error');
    expect(result).toEqual([]);
    expect(useDiagramStore.getState().diagramSummaries).toEqual([]);
  });

  it('sets isLoading during operation', async () => {
    let resolveFn: (v: any) => void;
    vi.mocked(apiClient.listDiagrams).mockReturnValue(
      new Promise((resolve) => { resolveFn = resolve; }),
    );

    const promise = useDiagramStore.getState().listDiagramsFromServer();
    expect(useDiagramStore.getState().isLoading).toBe(true);

    resolveFn!({ ok: true, data: [] });
    await promise;
    expect(useDiagramStore.getState().isLoading).toBe(false);
  });
});

describe('DiagramStore - deleteDiagramFromServer', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('calls apiClient.deleteDiagram and shows success toast', async () => {
    vi.mocked(apiClient.deleteDiagram).mockResolvedValue({ ok: true, data: undefined });

    await useDiagramStore.getState().deleteDiagramFromServer('diagram-del');

    expect(apiClient.deleteDiagram).toHaveBeenCalledWith('diagram-del');
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.message === 'Diagram deleted' && t.type === 'success')).toBe(true);
  });

  it('clears currentDiagramId if deleting the current diagram', async () => {
    useDiagramStore.setState({ currentDiagramId: 'diagram-del' });
    vi.mocked(apiClient.deleteDiagram).mockResolvedValue({ ok: true, data: undefined });

    await useDiagramStore.getState().deleteDiagramFromServer('diagram-del');

    expect(useDiagramStore.getState().currentDiagramId).toBeNull();
  });

  it('does not clear currentDiagramId if deleting a different diagram', async () => {
    useDiagramStore.setState({ currentDiagramId: 'other-diagram' });
    vi.mocked(apiClient.deleteDiagram).mockResolvedValue({ ok: true, data: undefined });

    await useDiagramStore.getState().deleteDiagramFromServer('diagram-del');

    expect(useDiagramStore.getState().currentDiagramId).toBe('other-diagram');
  });

  it('removes deleted diagram from diagramSummaries', async () => {
    useDiagramStore.setState({
      diagramSummaries: [
        { diagram_id: 'd1', project_name: 'A', updated_at: '2024-01-01T00:00:00Z' },
        { diagram_id: 'd2', project_name: 'B', updated_at: '2024-01-02T00:00:00Z' },
      ],
    });
    vi.mocked(apiClient.deleteDiagram).mockResolvedValue({ ok: true, data: undefined });

    await useDiagramStore.getState().deleteDiagramFromServer('d1');

    expect(useDiagramStore.getState().diagramSummaries).toEqual([
      { diagram_id: 'd2', project_name: 'B', updated_at: '2024-01-02T00:00:00Z' },
    ]);
  });

  it('shows error toast on failure', async () => {
    vi.mocked(apiClient.deleteDiagram).mockResolvedValue({
      ok: false,
      error: { type: 'http', status: 403, message: 'Forbidden' },
    });
    const addToast = vi.spyOn(useToastStore.getState(), 'addToast');

    await useDiagramStore.getState().deleteDiagramFromServer('diagram-del');

    expect(addToast).toHaveBeenCalledWith('Forbidden', 'error');
  });
});
