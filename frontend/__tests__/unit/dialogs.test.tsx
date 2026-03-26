import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import NewDiagramDialog from '@/components/menu/NewDiagramDialog';
import ProjectSettingsDialog from '@/components/menu/ProjectSettingsDialog';
import { useDiagramStore } from '@/store/diagram-store';

function resetStore() {
  useDiagramStore.setState({
    elements: new Map(),
    connectors: new Map(),
    viewport: { offsetX: 0, offsetY: 0, scale: 1 },
    projectName: '',
    environments: [],
    selectedElementId: null,
    selectedConnectorId: null,
    pendingConnectorSourceId: null,
    activeTool: 'pointer',
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

describe('NewDiagramDialog', () => {
  beforeEach(resetStore);

  it('does not render when open is false', () => {
    render(<NewDiagramDialog open={false} onClose={vi.fn()} />);
    expect(screen.queryByTestId('new-diagram-overlay')).toBeNull();
  });

  it('renders confirmation message when open', () => {
    render(<NewDiagramDialog open={true} onClose={vi.fn()} />);
    expect(screen.getByTestId('new-diagram-dialog')).toBeDefined();
    expect(screen.getByText(/Create a new diagram/)).toBeDefined();
  });

  it('calls onClose when Cancel is clicked', () => {
    const onClose = vi.fn();
    render(<NewDiagramDialog open={true} onClose={onClose} />);
    fireEvent.click(screen.getByTestId('new-diagram-cancel'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('clears store state and calls onClose on Confirm', () => {
    // Set up some state first
    const store = useDiagramStore.getState();
    store.addElement('lambda', { x: 100, y: 200 });
    store.addElement('s3', { x: 300, y: 400 });
    store.setProjectName('test-project');
    store.setEnvironments([{ name: 'dev', variables: { key: 'val' } }]);

    expect(useDiagramStore.getState().elements.size).toBe(2);
    expect(useDiagramStore.getState().projectName).toBe('test-project');

    const onClose = vi.fn();
    render(<NewDiagramDialog open={true} onClose={onClose} />);
    fireEvent.click(screen.getByTestId('new-diagram-confirm'));

    const state = useDiagramStore.getState();
    expect(state.elements.size).toBe(0);
    expect(state.connectors.size).toBe(0);
    expect(state.viewport).toEqual({ offsetX: 0, offsetY: 0, scale: 1 });
    expect(state.projectName).toBe('');
    expect(state.environments).toEqual([]);
    expect(state._undoStack).toEqual([]);
    expect(state._redoStack).toEqual([]);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('closes on Escape key', () => {
    const onClose = vi.fn();
    render(<NewDiagramDialog open={true} onClose={onClose} />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('closes when clicking the overlay', () => {
    const onClose = vi.fn();
    render(<NewDiagramDialog open={true} onClose={onClose} />);
    fireEvent.click(screen.getByTestId('new-diagram-overlay'));
    expect(onClose).toHaveBeenCalledOnce();
  });
});

describe('ProjectSettingsDialog', () => {
  beforeEach(resetStore);

  it('does not render when open is false', () => {
    render(<ProjectSettingsDialog open={false} onClose={vi.fn()} />);
    expect(screen.queryByTestId('project-settings-overlay')).toBeNull();
  });

  it('renders form when open', () => {
    render(<ProjectSettingsDialog open={true} onClose={vi.fn()} />);
    expect(screen.getByTestId('project-settings-dialog')).toBeDefined();
    expect(screen.getByTestId('project-name-input')).toBeDefined();
  });

  it('populates form with current store values', () => {
    useDiagramStore.getState().setProjectName('my-project');
    useDiagramStore.getState().setEnvironments([
      { name: 'prod', variables: { API_KEY: 'abc123' } },
    ]);

    render(<ProjectSettingsDialog open={true} onClose={vi.fn()} />);

    const nameInput = screen.getByTestId('project-name-input') as HTMLInputElement;
    expect(nameInput.value).toBe('my-project');
    expect(screen.getByTestId('env-name-0')).toBeDefined();
    expect((screen.getByTestId('env-name-0') as HTMLInputElement).value).toBe('prod');
    expect((screen.getByTestId('var-key-0-0') as HTMLInputElement).value).toBe('API_KEY');
    expect((screen.getByTestId('var-value-0-0') as HTMLInputElement).value).toBe('abc123');
  });

  it('saves project name and environments to store on Save', () => {
    render(<ProjectSettingsDialog open={true} onClose={vi.fn()} />);

    const nameInput = screen.getByTestId('project-name-input');
    fireEvent.change(nameInput, { target: { value: 'new-project' } });

    // Add an environment
    fireEvent.click(screen.getByTestId('add-environment-btn'));
    fireEvent.change(screen.getByTestId('env-name-0'), { target: { value: 'staging' } });

    // Add a variable
    fireEvent.click(screen.getByTestId('add-var-0'));
    fireEvent.change(screen.getByTestId('var-key-0-0'), { target: { value: 'DB_HOST' } });
    fireEvent.change(screen.getByTestId('var-value-0-0'), { target: { value: 'localhost' } });

    fireEvent.click(screen.getByTestId('project-settings-save'));

    const state = useDiagramStore.getState();
    expect(state.projectName).toBe('new-project');
    expect(state.environments).toEqual([
      { name: 'staging', variables: { DB_HOST: 'localhost' } },
    ]);
  });

  it('does not save on Cancel', () => {
    useDiagramStore.getState().setProjectName('original');
    const onClose = vi.fn();
    render(<ProjectSettingsDialog open={true} onClose={onClose} />);

    fireEvent.change(screen.getByTestId('project-name-input'), { target: { value: 'changed' } });
    fireEvent.click(screen.getByTestId('project-settings-cancel'));

    expect(useDiagramStore.getState().projectName).toBe('original');
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('closes on Escape key', () => {
    const onClose = vi.fn();
    render(<ProjectSettingsDialog open={true} onClose={onClose} />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('can add and remove environments', () => {
    render(<ProjectSettingsDialog open={true} onClose={vi.fn()} />);

    fireEvent.click(screen.getByTestId('add-environment-btn'));
    fireEvent.click(screen.getByTestId('add-environment-btn'));
    expect(screen.getByTestId('environment-0')).toBeDefined();
    expect(screen.getByTestId('environment-1')).toBeDefined();

    fireEvent.click(screen.getByTestId('remove-env-0'));
    expect(screen.queryByTestId('environment-1')).toBeNull();
    expect(screen.getByTestId('environment-0')).toBeDefined();
  });

  it('can add and remove variables within an environment', () => {
    render(<ProjectSettingsDialog open={true} onClose={vi.fn()} />);

    fireEvent.click(screen.getByTestId('add-environment-btn'));
    fireEvent.click(screen.getByTestId('add-var-0'));
    fireEvent.click(screen.getByTestId('add-var-0'));

    expect(screen.getByTestId('var-key-0-0')).toBeDefined();
    expect(screen.getByTestId('var-key-0-1')).toBeDefined();

    fireEvent.click(screen.getByTestId('remove-var-0-0'));
    expect(screen.getByTestId('var-key-0-0')).toBeDefined();
    expect(screen.queryByTestId('var-key-0-1')).toBeNull();
  });
});
