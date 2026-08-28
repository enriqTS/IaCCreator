import { beforeEach, describe, expect, it } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import Minimap from '@/components/canvas/Minimap';
import SemanticContainerComponent from '@/components/canvas/objects/SemanticContainerComponent';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock, CanvasObject, SemanticContainerObject } from '@/types/diagram';

function container(id: string, parentContainerId?: string): SemanticContainerObject {
  return {
    id,
    objectType: 'semantic-container',
    containerType: 'generic',
    name: id,
    position: { x: 100, y: 100 },
    config: {},
    visualConfig: { width: 200, height: 150, fillColor: '#000', borderColor: '#fff', borderWidth: 1 },
    zIndex: 0,
    parentContainerId,
  };
}

function resource(id: string, parentContainerId?: string): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'vpc',
    name: id,
    position: { x: 100, y: 100 },
    config: {},
    terraformVariables: {},
    visualConfig: { width: 100, height: 80 },
    zIndex: 1,
    parentContainerId,
    presentation: 'container',
  };
}

function reset(objects: CanvasObject[] = []) {
  useDiagramStore.setState({
    canvasObjects: new Map(objects.map((object) => [object.id, object])),
    connectors: new Map(),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    activeContainmentTargetId: null,
    activeContainmentTargetValid: null,
    _undoStack: [],
    _redoStack: [],
  });
}

describe('semantic containment rendering', () => {
  beforeEach(() => reset());

  it('renders nested boundaries and valid and invalid target states', () => {
    const scope = container('scope');
    reset([scope]);
    const view = render(<SemanticContainerComponent object={scope} isSelected={false} />);
    expect(screen.getByTestId('semantic-container-scope').getAttribute('data-container-type')).toBe('generic');

    act(() => useDiagramStore.setState({ activeContainmentTargetId: 'scope', activeContainmentTargetValid: true }));
    expect(screen.getByTestId('semantic-container-scope').getAttribute('data-drop-target')).toBe('valid');
    act(() => useDiagramStore.setState({ activeContainmentTargetValid: false }));
    expect(screen.getByTestId('semantic-container-scope').getAttribute('data-drop-target')).toBe('invalid');
    view.unmount();
  });

  it('persists collapse state in history and hides the full boundary', () => {
    const scope = container('scope');
    reset([scope]);
    render(<SemanticContainerComponent object={scope} isSelected={false} />);

    fireEvent.click(screen.getByRole('button', { name: 'Collapse scope' }));

    expect(useDiagramStore.getState().canvasObjects.get('scope')?.collapsed).toBe(true);
    expect(useDiagramStore.getState().canUndo).toBe(true);
    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().canvasObjects.get('scope')?.collapsed).toBeFalsy();
  });

  it('renders scope and resource containers in the minimap', () => {
    reset([container('scope'), resource('vpc', 'scope')]);
    const { container: rendered } = render(<Minimap />);
    const colors = [...rendered.querySelectorAll('rect')].map((rect) => rect.getAttribute('fill'));

    expect(colors).toContain('#334155');
    expect(colors).toContain('#1d4f73');
  });

  it('round trips semantic and visual grouping independently', () => {
    const scope = container('scope');
    const child = { ...resource('child', 'scope'), groupId: 'visual-group', collapsed: true };
    reset([scope, child]);
    useDiagramStore.setState({
      objectGroups: new Map([['visual-group', { id: 'visual-group', name: 'Visual', memberIds: ['child', 'scope'] }]]),
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    reset();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored = useDiagramStore.getState().canvasObjects.get('child');
    expect(restored?.parentContainerId).toBe('scope');
    expect(restored?.groupId).toBe('visual-group');
    expect(restored?.collapsed).toBe(true);
    expect(useDiagramStore.getState().objectGroups.get('visual-group')?.memberIds).toEqual(['child', 'scope']);
  });
});
