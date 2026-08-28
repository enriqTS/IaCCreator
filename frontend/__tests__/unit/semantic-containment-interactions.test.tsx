import fc from 'fast-check';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import CanvasObjectContextMenu from '@/components/canvas/interactions/CanvasObjectContextMenu';
import ElementLayer from '@/components/canvas/ElementLayer';
import { apiClient } from '@/utils/api-client';
import { useDiagramStore } from '@/store/diagram-store';
import { useEditorDomainStore } from '@/store/editor-domain-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { useSnapDrag } from '@/hooks/useSnapDrag';
import type { ArchitectureBlock, CanvasObject, LineObject, SemanticContainerObject } from '@/types/diagram';

function container(id: string, parentContainerId?: string): SemanticContainerObject {
  return {
    id,
    objectType: 'semantic-container',
    containerType: 'generic',
    name: id,
    position: { x: 100, y: 100 },
    config: {},
    visualConfig: { width: 300, height: 250, fillColor: '#000', borderColor: '#fff', borderWidth: 1 },
    zIndex: 0,
    parentContainerId,
  };
}

function resource(id: string, parentContainerId?: string): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: id,
    position: { x: 100, y: 100 },
    config: {},
    terraformVariables: {},
    visualConfig: { width: 80, height: 80 },
    zIndex: 2,
    parentContainerId,
  };
}

function reset(objects: CanvasObject[]) {
  useDiagramStore.setState({
    canvasObjects: new Map(objects.map((object) => [object.id, object])),
    connectors: new Map(),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    pendingContainmentObjectId: null,
    activeContainmentTargetId: null,
    activeContainmentTargetValid: null,
    containmentDragStartParentId: null,
    activeTool: 'pointer',
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
  useEditorDomainStore.setState({
    containmentRules: [{ child_type: 'lambda', parent_type: 'generic' }],
  });
  useLayoutPreferencesStore.setState({ snapToGridEnabled: false, alignmentGuidesEnabled: false });
}

function DragHarness() {
  const { handleMouseDown } = useSnapDrag({ objectId: 'child', isSelected: true });
  return <button type="button" onPointerDown={handleMouseDown}>Drag child</button>;
}

function successfulResponse(parentContainerId?: string) {
  const diagram = useDiagramStore.getState().serializeDiagramState();
  const child = diagram.canvasObjects.find((object) => object.id === 'child')!;
  child.parentContainerId = parentContainerId;
  return {
    ok: true as const,
    data: {
      diagram,
      resolution: { effective_scopes: [], inherited_values: [], issues: [] },
    },
  };
}

describe('semantic containment interactions', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    reset([container('first'), container('second'), resource('child')]);
  });

  it('drags into, between, and out of containers through the interaction hook', async () => {
    reset([
      { ...container('first'), position: { x: 100, y: 100 } },
      { ...container('second'), position: { x: 500, y: 100 } },
      { ...resource('child'), position: { x: 900, y: 100 } },
    ]);
    useDiagramStore.setState({ selectedObjectIds: new Set(['child']) });
    const operation = vi.spyOn(apiClient, 'applyContainmentOperation');
    operation.mockImplementation(async (_diagram, intent) => successfulResponse(
      intent.operation === 'remove' ? undefined : intent.parent_id as string,
    ));
    render(<DragHarness />);
    const drag = screen.getByRole('button', { name: 'Drag child' });

    fireEvent.pointerDown(drag, { button: 0, clientX: 900, clientY: 100 });
    fireEvent.pointerMove(window, { clientX: 100, clientY: 100 });
    fireEvent.pointerUp(window, { clientX: 100, clientY: 100 });
    await waitFor(() => expect(useDiagramStore.getState().canvasObjects.get('child')?.parentContainerId).toBe('first'));

    fireEvent.pointerDown(drag, { button: 0, clientX: 100, clientY: 100 });
    fireEvent.pointerMove(window, { clientX: 500, clientY: 100 });
    fireEvent.pointerUp(window, { clientX: 500, clientY: 100 });
    await waitFor(() => expect(useDiagramStore.getState().canvasObjects.get('child')?.parentContainerId).toBe('second'));

    fireEvent.pointerDown(drag, { button: 0, clientX: 500, clientY: 100 });
    fireEvent.pointerMove(window, { clientX: 900, clientY: 100 });
    fireEvent.pointerUp(window, { clientX: 900, clientY: 100 });
    await waitFor(() => expect(useDiagramStore.getState().canvasObjects.get('child')?.parentContainerId).toBeUndefined());
    expect(operation.mock.calls.map((call) => call[1].operation)).toEqual(['assign', 'assign', 'remove']);
  });

  it('preserves hierarchy invariants through arbitrary assign, reparent, remove, and delete sequences', async () => {
    await fc.assert(fc.asyncProperty(
      fc.array(fc.oneof(
        fc.record({ operation: fc.constant('assign'), parentId: fc.constantFrom('first', 'second') }),
        fc.record({ operation: fc.constant('remove'), parentId: fc.constant(undefined) }),
        fc.record({ operation: fc.constant('delete'), parentId: fc.constantFrom('first', 'second', 'child') }),
      ), { minLength: 1, maxLength: 30 }),
      async (operations) => {
        reset([container('first'), container('second'), resource('child')]);
        vi.spyOn(apiClient, 'applyContainmentOperation').mockImplementation(async (_diagram, intent) => successfulResponse(
          intent.operation === 'remove' ? undefined : intent.parent_id as string,
        ));

        for (const operation of operations) {
          const state = useDiagramStore.getState();
          if (operation.operation === 'delete') {
            state.removeCanvasObject(operation.parentId);
          } else if (state.canvasObjects.has('child')) {
            const parentId = operation.operation === 'assign' && state.canvasObjects.has(operation.parentId)
              ? operation.parentId
              : null;
            await state.assignSemanticParent('child', parentId);
          }

          for (const object of useDiagramStore.getState().canvasObjects.values()) {
            if ('parentContainerId' in object && object.parentContainerId) {
              expect(useDiagramStore.getState().canvasObjects.has(object.parentContainerId)).toBe(true);
              expect(object.parentContainerId).not.toBe(object.id);
            }
          }
        }
      },
    ), { numRuns: 50 });
  });

  it('assigns, reparents, and removes through backend-normalized operations', async () => {
    const operation = vi.spyOn(apiClient, 'applyContainmentOperation');
    operation.mockImplementation(async (_diagram, intent) => successfulResponse(
      intent.operation === 'remove' ? undefined : intent.parent_id as string,
    ));

    await useDiagramStore.getState().assignSemanticParent('child', 'first');
    expect(useDiagramStore.getState().canvasObjects.get('child')?.parentContainerId).toBe('first');
    await useDiagramStore.getState().assignSemanticParent('child', 'second');
    expect(useDiagramStore.getState().canvasObjects.get('child')?.parentContainerId).toBe('second');
    await useDiagramStore.getState().assignSemanticParent('child', null);
    expect(useDiagramStore.getState().canvasObjects.get('child')?.parentContainerId).toBeUndefined();

    expect(operation.mock.calls.map((call) => call[1].operation)).toEqual(['assign', 'assign', 'remove']);
    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().canvasObjects.get('child')?.parentContainerId).toBe('second');
  });

  it('preserves canonical state after client-side and backend rejection', async () => {
    const before = useDiagramStore.getState().canvasObjects;
    useDiagramStore.getState().beginContainmentDrag('child');
    useDiagramStore.getState().updateContainmentTarget('first', false);
    await useDiagramStore.getState().finishContainmentDrag('child');
    expect(useDiagramStore.getState().canvasObjects).toBe(before);

    vi.spyOn(apiClient, 'applyContainmentOperation').mockResolvedValue({
      ok: true,
      data: {
        diagram: useDiagramStore.getState().serializeDiagramState(),
        resolution: {
          effective_scopes: [],
          inherited_values: [],
          issues: [{ severity: 'error', message: 'Rejected by backend' }],
        },
      },
    });
    const snapshot = useDiagramStore.getState().canvasObjects;
    await useDiagramStore.getState().assignSemanticParent('child', 'first');
    expect(useDiagramStore.getState().canvasObjects).toBe(snapshot);
    expect(useDiagramStore.getState().pendingContainmentObjectId).toBeNull();
  });

  it('exposes move, remove, and select-container context actions', async () => {
    vi.spyOn(apiClient, 'applyContainmentOperation').mockImplementation(async (_diagram, intent) => successfulResponse(intent.parent_id as string | undefined));
    useDiagramStore.setState({ selectedObjectIds: new Set(['child']) });
    const close = vi.fn();
    const view = render(<CanvasObjectContextMenu menu={{ objectId: 'child', x: 0, y: 0 }} onClose={close} />);

    fireEvent.click(screen.getByText('Move into first'));
    await waitFor(() => expect(useDiagramStore.getState().canvasObjects.get('child')?.parentContainerId).toBe('first'));
    view.unmount();

    render(<CanvasObjectContextMenu menu={{ objectId: 'child', x: 0, y: 0 }} onClose={close} />);
    fireEvent.click(screen.getByText('Select Container'));
    expect(useDiagramStore.getState().selectedObjectIds).toEqual(new Set(['first']));
  });

  it('offers explicit reparent and cascade choices when deleting a container', () => {
    reset([container('parent'), container('nested', 'parent'), resource('child', 'nested')]);
    useDiagramStore.setState({ selectedObjectIds: new Set(['nested']) });
    const first = render(<CanvasObjectContextMenu menu={{ objectId: 'nested', x: 0, y: 0 }} onClose={vi.fn()} />);

    fireEvent.click(screen.getByText('Delete and Reparent Contents'));
    expect(useDiagramStore.getState().canvasObjects.has('nested')).toBe(false);
    expect(useDiagramStore.getState().canvasObjects.get('child')?.parentContainerId).toBe('parent');
    first.unmount();

    reset([container('parent'), container('nested', 'parent'), resource('child', 'nested')]);
    useDiagramStore.setState({ selectedObjectIds: new Set(['nested']) });
    render(<CanvasObjectContextMenu menu={{ objectId: 'nested', x: 0, y: 0 }} onClose={vi.fn()} />);
    fireEvent.click(screen.getByText('Delete Subtree'));
    expect(useDiagramStore.getState().canvasObjects.has('nested')).toBe(false);
    expect(useDiagramStore.getState().canvasObjects.has('child')).toBe(false);
    expect(useDiagramStore.getState().canvasObjects.has('parent')).toBe(true);
  });

  it('hides and restores descendant connectors when a boundary collapses', () => {
    const scope = { ...container('scope'), collapsed: true };
    const child = resource('child', 'scope');
    const outside = resource('outside');
    const line: LineObject = {
      id: 'line',
      objectType: 'line',
      name: 'line',
      start: { x: 100, y: 100 },
      end: { x: 400, y: 100 },
      visualConfig: { strokeColor: '#fff', strokeWidth: 2, strokeStyle: 'solid', routingMode: 'diagonal' },
      zIndex: 3,
      sourceAnchor: { objectId: 'child', anchorPosition: 'right' },
      targetAnchor: { objectId: 'outside', anchorPosition: 'left' },
      waypoints: null,
    };
    reset([scope, child, outside, line]);
    const view = render(<ElementLayer />);
    expect(screen.queryByTestId('line-svg-overlay')).toBeNull();

    act(() => useDiagramStore.getState().toggleContainerCollapsed('scope'));
    view.rerender(<ElementLayer />);
    expect(screen.getByTestId('line-svg-overlay')).not.toBeNull();
  });
});
